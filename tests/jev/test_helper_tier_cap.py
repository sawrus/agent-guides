"""Lean helpers (explorer, reviewer) never route above the session model's tier; an unknown tier caps at balanced."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import hook
import routing

LUNA, SOL, ASTRA = 'gpt-6-luna', 'gpt-6.1-sol', 'gpt-6-astra'
DEFAULTS = {'roles': {}, 'tiers': {'fast': LUNA, 'balanced': SOL, 'frontier': ASTRA}}


def models(*ids):
    return [{'id': i, 'description': '', 'prices': None} for i in ids]


def plan(ids, **event):
    return routing.plan_spawn({'host': 'codex', 'agent': 'reviewer', 'profile': 'lean', **event}, models(*ids), DEFAULTS, {})


class HelperTierCap(unittest.TestCase):
    def test_single_frontier_model_falls_back_for_an_unknown_session_tier(self):
        result = plan([ASTRA], session_model='gpt-5.6-terra')
        self.assertEqual(result['result'], {'status': 'fallback', 'reason_code': 'tier_above_session'})
        self.assertTrue(result['keep_native'])
        self.assertEqual(plan([ASTRA])['result']['reason_code'], 'tier_above_session')

    def test_single_model_within_the_session_tier_is_still_routed(self):
        self.assertEqual(plan([ASTRA], session_model=ASTRA)['result']['reason_code'], 'single_eligible_model')
        self.assertEqual(plan([SOL])['result']['reason_code'], 'single_eligible_model')
        self.assertEqual(plan([SOL], session_model=LUNA)['result']['reason_code'], 'tier_above_session')

    def test_pool_is_capped_at_the_session_tier(self):
        self.assertEqual([c['tier'] for c in plan([LUNA, SOL, ASTRA])['pool']], ['fast', 'balanced'])
        self.assertEqual([c['tier'] for c in plan([LUNA, SOL, ASTRA], session_model=ASTRA)['pool']],
                         ['fast', 'balanced', 'frontier'])
        capped = plan([LUNA, SOL, ASTRA], session_model=LUNA)['result']
        self.assertEqual((capped['reason_code'], capped['model']), ('single_eligible_model', LUNA))

    def test_other_roles_profiles_and_pins_are_unchanged(self):
        self.assertEqual(plan([ASTRA], agent='developer')['result']['reason_code'], 'single_eligible_model')
        self.assertEqual(plan([ASTRA], profile='team')['result']['reason_code'], 'single_eligible_model')
        self.assertEqual(plan([ASTRA], pinned_model=ASTRA)['result']['reason_code'], 'explicit_model_or_continuation')

    def test_role_default_above_the_cap_is_not_applied(self):
        defaults = {'roles': {'reviewer': ASTRA}, 'tiers': DEFAULTS['tiers']}
        event = {'host': 'codex', 'agent': 'reviewer', 'profile': 'lean'}
        for ids, expected in (([ASTRA], None), ([ASTRA, LUNA], LUNA)):
            result = routing.plan_spawn(event, models(*ids), defaults, {})
            routing.apply_role_default(result)
            self.assertEqual(result['result'].get('model'), expected, ids)
        self.assertIsNone(routing.plan_spawn(event, models(ASTRA, SOL, LUNA), defaults, {})['role_default'])

    def test_opencode_and_claude_session_tiers(self):
        tier_map = routing.load_tier_map({'version': 1, 'roles': {}, 'providers': {
            'openai': {'fast': 'openai/' + LUNA, 'balanced': 'openai/' + SOL, 'frontier': 'openai/' + ASTRA}}})
        event = {'host': 'opencode', 'agent': 'explorer', 'profile': 'lean', 'session_model': 'openai/' + ASTRA}
        ids = ['openai/' + m for m in (LUNA, SOL, ASTRA)]
        self.assertEqual(len(routing.plan_spawn(event, models(*ids), {'roles': {}, 'tiers': {}}, {}, tier_map)['pool']), 3)
        claude = {'host': 'claude', 'agent': 'explorer', 'profile': 'lean', 'session_model': 'claude-haiku-4-5'}
        capped = routing.plan_spawn(claude, [dict(m) for m in routing.CLAUDE_MODELS], {'roles': {}, 'tiers': {}}, {})
        self.assertEqual(capped['result']['model'], 'haiku')
        claude['session_model'] = 'claude-sonnet-5'
        capped = routing.plan_spawn(claude, [dict(m) for m in routing.CLAUDE_MODELS], {'roles': {}, 'tiers': {}}, {})
        self.assertEqual([c['model'] for c in capped['pool']], ['haiku', 'sonnet'])


class ClaudeSpawn(unittest.TestCase):
    """End to end: Claude reads the session model from the main transcript and the lean profile from the manifest."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {'HOME': str(self.project / 'home')}, clear=True)
        self.environment.start()
        (self.project / '.agentic.json').write_text(json.dumps({'settings': {'jev': {'enabled': True}, 'profile': 'lean'}}))
        (self.project / '.claude/agents').mkdir(parents=True)
        (self.project / '.claude/agents/explorer.md').write_text('---\nname: explorer\ndescription: explorer\n---\n')

    def tearDown(self):
        self.environment.stop()
        self.temp.cleanup()

    def test_haiku_session_never_routes_a_helper_up(self):
        transcript = self.project / 'main.jsonl'
        transcript.write_text(json.dumps({'type': 'assistant', 'message': {'model': 'claude-haiku-4-5'}}) + '\n')
        payload = {'hook_event_name': 'PreToolUse', 'session_id': 'root', 'transcript_path': str(transcript),
                   'cwd': str(self.project), 'tool_name': 'Agent', 'tool_use_id': 't1',
                   'tool_input': {'subagent_type': 'explorer', 'prompt': 'find the export code'}}
        with patch.object(hook, 'evaluate', side_effect=AssertionError('one tier left: no question')):
            out = hook.claude_event(self.project, payload)
        self.assertEqual(out['hookSpecificOutput']['updatedInput']['model'], 'haiku')
        records = [json.loads(p.read_text()) for p in (self.project / '.agentic/jev').glob('event-*.json')]
        spawn = next(r for r in records if r['context']['kind'] == 'spawn')
        self.assertEqual((spawn['context']['profile'], spawn['context']['session_model']), ('lean', 'claude-haiku-4-5'))
        self.assertEqual(spawn['result']['reason_code'], 'single_eligible_model')


if __name__ == '__main__':
    unittest.main()
