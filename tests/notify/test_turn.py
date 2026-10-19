"""Turn facts for the Telegram header: final-turn rule per host, agent and model sources."""
import json
import os
from pathlib import Path
import tempfile
import unittest

import telegram
import telegram_turn as turn

FIXTURES = Path(__file__).resolve().parent / 'fixtures'


def notification(task_id, status='completed', note=''):
    note = f'\n<note>{note}</note>' if note else ''
    return f'<task-notification>\n<task-id>{task_id}</task-id>\n<status>{status}</status>{note}\n</task-notification>'


def delivered(task_id, **kwargs):
    return {'type': 'user', 'message': {'content': notification(task_id, **kwargs)}}


def launched(**result):
    return {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'content': 'ok'}]}, 'toolUseResult': result}


def assistant(model, **extra):
    return {'type': 'assistant', 'message': {'model': model, 'content': [{'type': 'text', 'text': 'x'}]}, **extra}


class TurnFacts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / 'calc-app'
        (self.project / '.claude').mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def transcript(self, entries, name='t.jsonl'):
        path = self.root / name
        path.write_text('\n'.join(json.dumps(entry) for entry in entries) + '\n')
        return str(path)

    def facts(self, payload, host='claude', with_final=True):
        return turn.turn_facts(host, payload, self.project, telegram.read_json, with_final)

    def test_claude_host_task_lists_decide_first(self):
        clean = self.transcript([assistant('claude-opus-5-5')])
        self.assertFalse(self.facts({'background_tasks': [{'id': 'b1'}], 'transcript_path': clean})['final'])
        self.assertFalse(self.facts({'background_tasks': [], 'session_crons': [{'id': 'c1'}]})['final'])
        self.assertTrue(self.facts({'background_tasks': []})['final'])
        self.assertTrue(self.facts({'background_tasks': [], 'transcript_path': str(self.root / 'missing.jsonl')})['final'])
        self.assertFalse(self.facts({})['final'])
        self.assertTrue(self.facts({'transcript_path': clean})['final'])

    def test_resumed_agent_is_pending_until_it_notifies_again(self):
        entries = [launched(isAsync=True, status='async_launched', agentId='a1'), delivered('a1')]
        self.assertEqual(turn.claude_pending(entries), set())
        entries.append(launched(success=True, resumedAgentId='a1'))
        self.assertEqual(turn.claude_pending(entries), {'a1'})
        entries.append(delivered('a1', status='failed'))
        self.assertEqual(turn.claude_pending(entries), set())

    def test_pending_rules_for_background_bash_text_fallback_and_status(self):
        text_only = {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'content': [
            {'type': 'text', 'text': 'Async agent launched successfully.\nagentId: t1 (internal)'}]}]}}
        bash_text = {'type': 'user', 'message': {'content': [{'type': 'tool_result',
                                                               'content': 'Command running in background with ID: b2.'}]}}
        entries = [launched(backgroundTaskId='b1'), text_only, bash_text, delivered('b1', status='running'),
                   delivered('t1', status='killed'), {'type': 'queue-operation', 'operation': 'enqueue',
                                                      'content': notification('b2')}]
        self.assertEqual(turn.claude_pending(entries), {'b1', 'b2'})
        quoted = {'type': 'assistant', 'message': {'content': 'Command running in background with ID: q1.'}}
        self.assertEqual(turn.claude_pending([quoted]), set())

    def test_text_only_launch_lines_reach_the_pending_scan(self):
        for name, text in (('agent.jsonl', 'Async agent launched successfully.\nagentId: t1 (internal ID)'),
                           ('bash.jsonl', 'Command running in background with ID: b2. Output is being written')):
            line = {'type': 'user', 'message': {'role': 'user', 'content': [
                {'type': 'tool_result', 'tool_use_id': 'tu1', 'content': [{'type': 'text', 'text': text}]}]}}
            path = self.transcript([assistant('claude-opus-5-5'), line], name=name)
            with self.subTest(name):
                self.assertFalse(self.facts({'transcript_path': path})['final'])
                self.assertFalse(self.facts({'transcript_path': path, 'background_tasks': []})['final'])

    def test_interim_note_is_settled_only_by_the_host_task_list(self):
        still_running = 'The agent reported back, but it has background work of its own still running.'
        entries = [launched(isAsync=True, status='async_launched', agentId='a1'), delivered('a1', note=still_running)]
        path = self.transcript(entries)
        self.assertTrue(self.facts({'transcript_path': path, 'background_tasks': []})['final'])
        self.assertFalse(self.facts({'transcript_path': path})['final'])
        self.assertFalse(self.facts({'transcript_path': path, 'background_tasks': 'n/a'})['final'])
        self.assertEqual(turn.claude_pending_state(entries), ({'a1'}, {'a1'}))
        resumed = self.transcript(entries + [launched(success=True, resumedAgentId='a1')], name='resumed.jsonl')
        self.assertFalse(self.facts({'transcript_path': resumed, 'background_tasks': []})['final'])
        bash = self.transcript(entries + [launched(backgroundTaskId='b1')], name='bash.jsonl')
        self.assertFalse(self.facts({'transcript_path': bash, 'background_tasks': []})['final'])
        done = self.transcript(entries + [delivered('a1')], name='done.jsonl')
        self.assertTrue(self.facts({'transcript_path': done})['final'])

    def test_malformed_entries_are_skipped_without_losing_facts(self):
        path = self.transcript([{'type': 'agent-setting', 'agentSetting': 'product-owner'}, assistant('claude-opus-5-5'),
                                {'type': 'user', 'message': 'toolUseResult'},
                                {'type': 'user', 'message': ['<task-notification>']},
                                {'type': 'attachment', 'attachment': 'toolUseResult'},
                                {'type': 'assistant', 'message': 'claude-x'}])
        self.assertEqual(self.facts({'transcript_path': path, 'background_tasks': []}),
                         {'agent': 'product-owner', 'model': 'claude-opus-5-5', 'final': True})
        rollout = self.transcript([
            {'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'spawn_agent', 'arguments': '{"task_name":"pm"}'}},
            {'type': 'response_item', 'payload': {'type': 'agent_message', 'author': '/root/pm', 'content': 7, 'id': 'FINAL_ANSWER'}},
            {'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'spawn_agent', 'arguments': 5}},
            {'type': 'response_item', 'payload': 'spawn_agent'}], name='rollout.jsonl')
        facts = self.facts({'transcript_path': rollout, 'model': 'gpt-6-astra'}, host='codex')
        self.assertEqual(facts, {'agent': None, 'model': 'gpt-6-astra', 'final': False})

    def test_sidechain_and_api_request_entries_are_ignored(self):
        path = self.transcript([{**launched(isAsync=True, status='async_launched', agentId='a1'), 'isSidechain': True},
                                {'type': 'api-request-start', 'toolUseResult': {'backgroundTaskId': 'b9'}}])
        self.assertTrue(self.facts({'transcript_path': path})['final'])

    def test_claude_agent_and_model_precedence(self):
        path = self.transcript([{'type': 'agent-setting', 'agentSetting': 'product-owner'},
                                {'type': 'agent-name', 'agentName': 'my-session'},
                                assistant('claude-opus-5-5'), assistant('claude-haiku-9', isSidechain=True),
                                assistant('<synthetic>')])
        facts = self.facts({'transcript_path': path, 'agent_type': 'team-lead'}, with_final=False)
        self.assertEqual(facts, {'agent': 'team-lead', 'model': 'claude-opus-5-5', 'final': False})
        facts = self.facts({'transcript_path': path, 'agent_type': 'developer', 'agent_id': 'sub1'})
        self.assertEqual((facts['agent'], facts['model']), ('product-owner', 'claude-opus-5-5'))
        (self.project / '.claude/settings.json').write_text(json.dumps({'agent': 'qa'}))
        self.assertEqual(self.facts({})['agent'], 'qa')
        (self.project / '.claude/settings.local.json').write_text(json.dumps({'agent': 'pm'}))
        self.assertEqual(self.facts({})['agent'], 'pm')
        only_name = self.transcript([{'type': 'agent-name', 'agentName': 'my-session'}], name='n.jsonl')
        (self.project / '.claude/settings.local.json').unlink()
        (self.project / '.claude/settings.json').unlink()
        self.assertEqual(self.facts({'transcript_path': only_name}), {'agent': None, 'model': None, 'final': True})

    def test_transcript_reads_are_safe(self):
        real = self.transcript([launched(backgroundTaskId='b1')])
        link = self.root / 'link.jsonl'
        os.symlink(real, link)
        self.assertIsNone(turn.transcript_entries(str(link), turn.CLAUDE_MARKERS))
        self.assertIsNone(turn.transcript_entries(str(self.root), turn.CLAUDE_MARKERS))
        self.assertIsNone(turn.transcript_entries(None, turn.CLAUDE_MARKERS))
        broken = self.root / 'broken.jsonl'
        broken.write_text('{"toolUseResult": \n["toolUseResult"]\n' + json.dumps(launched(backgroundTaskId='b1')) + '\n')
        self.assertEqual(len(turn.transcript_entries(str(broken), turn.CLAUDE_MARKERS)), 1)
        original, turn.SCAN_LIMIT = turn.SCAN_LIMIT, 10
        try:
            self.assertIsNone(turn.transcript_entries(real, turn.CLAUDE_MARKERS))
        finally:
            turn.SCAN_LIMIT = original

    def test_codex_children_and_null_transcript(self):
        lines = (FIXTURES / 'codex_rollout.jsonl').read_text().splitlines()
        full = self.transcript([json.loads(line) for line in lines], name='full.jsonl')
        open_developer = self.transcript([json.loads(line) for line in lines[:7]], name='open.jsonl')
        payload = {'model': 'gpt-6-astra', 'transcript_path': full, 'turn_id': 't1'}
        self.assertEqual(self.facts(payload, host='codex'), {'agent': None, 'model': 'gpt-6-astra', 'final': True})
        self.assertFalse(self.facts({**payload, 'transcript_path': open_developer}, host='codex')['final'])
        self.assertFalse(self.facts({**payload, 'transcript_path': None}, host='codex')['final'])
        self.assertEqual(self.facts({'agent_type': 'pm', 'model': 'x'}, host='codex')['agent'], 'pm')
        unkeyed = {'type': 'response_item', 'payload': {'type': 'function_call', 'name': 'spawn_agent', 'arguments': '{}'}}
        self.assertEqual(turn.codex_open_children([unkeyed]), {turn.CODEX_UNKEYED})

    def test_opencode_trusts_only_explicit_final(self):
        facts = self.facts({'agent': 'build', 'model': {'id': 'gpt-6-luna', 'providerID': 'openai'}, 'final': True},
                           host='opencode')
        self.assertEqual(facts, {'agent': 'build', 'model': 'gpt-6-luna', 'final': True})
        self.assertFalse(self.facts({'final': 'true'}, host='opencode')['final'])
        self.assertFalse(self.facts({'final': True}, host='opencode', with_final=False)['final'])

    def test_model_label_normalization(self):
        self.assertEqual(turn.model_label('openai/gpt-6-luna#high'), 'gpt-6-luna')
        self.assertEqual(turn.model_label({'modelID': 'gpt-6-luna'}), 'gpt-6-luna')
        self.assertEqual(turn.model_label('claude-opus-5-5'), 'claude-opus-5-5')
        self.assertIsNone(turn.model_label(None))
        self.assertIsNone(turn.model_label('  '))


if __name__ == '__main__':
    unittest.main()
