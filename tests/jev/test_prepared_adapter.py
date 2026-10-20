"""Prepare through the actual runtime, then submit an opaque native assignment."""
import json
import sys
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
import hook
import prepared
import test_hooks
import test_blackbox


class PreparedAdapter(unittest.TestCase):
    def setUp(self):
        self.fixture = test_hooks.Hooks()
        self.fixture.setUp()
        self.project = self.fixture.project
        self.fixture.write_defaults({'version': 2, 'roles': {'developer': 'balanced'},
            'tiers': {'fast': 'fast', 'balanced': 'balanced'}})
        hook.run_event(self.project, self.fixture.event('prompt', host='codex', prompt='/develop-feature calculator'))
        self.context_path = self.project / '.agentic/jev' / ('context-' + hook.short_hash('root') + '.json')
        self.task = json.loads(self.context_path.read_text())['task_id']
        self.pool = patch.object(hook, 'codex_models', return_value=[{'id': 'fast'}, {'id': 'balanced'}])
        self.pool.start()

    def tearDown(self):
        self.pool.stop()
        self.fixture.tearDown()

    def prepare(self, request='request'):
        return prepared.prepare(hook, self.project, {'session_id': 'root', 'task_id': self.task,
            'request_id': request, 'role': 'developer', 'goal': 'Implement arithmetic',
            'scope': 'one module, no deployment', 'complexity': 'routine, supplied interfaces'})

    def payload(self, result, tool='launch'):
        return {'hook_event_name': 'PreToolUse', 'session_id': 'root', 'tool_use_id': tool,
            'tool_name': 'collaboration.spawn_agent', 'tool_input': {**result['spawn'], 'message': 'gAAAA-opaque'}}

    def test_prepared_encrypted_launch_is_recorded_without_second_call(self):
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.fixture.answer(r, 'fast')) as evaluate:
            recommendation = self.prepare()
            payload = self.payload(recommendation)
            self.assertEqual(hook.codex_event(self.project, payload), {})
            self.assertEqual(hook.codex_event(self.project, payload), {})
        self.assertEqual(evaluate.call_count, 1)
        self.assertEqual(payload['tool_input']['message'], 'gAAAA-opaque')
        records = self.fixture.records('spawn')
        chosen = next(r for r in records if r['context'].get('preparation_only'))
        submitted = next(r for r in records if r['context'].get('prepared_decision'))
        self.assertFalse(chosen['applied'])
        self.assertEqual(chosen['outcome'], 'recommended_unconfirmed')
        self.assertEqual(submitted['result']['recommended_model'], 'fast')
        self.assertEqual(submitted['result']['submitted_model'], 'fast')
        self.assertIsNone(submitted['result']['observed_model'])
        self.assertFalse(submitted['applied'])
        self.assertNotIn('gAAAA', json.dumps(records))

    def test_two_same_role_assignments_do_not_cross(self):
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.fixture.answer(r, 'fast')) as evaluate:
            first, second = self.prepare('one'), self.prepare('two')
            hook.codex_event(self.project, self.payload(second, 'second'))
            hook.codex_event(self.project, self.payload(first, 'first'))
        self.assertEqual(evaluate.call_count, 2)
        for result, tool in ((first, 'first'), (second, 'second')):
            record = json.loads((self.project / '.agentic/jev' / ('prepared-' + result['decision_id'] + '.json')).read_text())
            self.assertEqual(record['tool_use_id'], tool)

    def test_native_child_link_and_observation_are_exact(self):
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.fixture.answer(r, 'fast')):
            selected = self.prepare()
        payload = self.payload(selected)
        hook.codex_event(self.project, payload)
        child = '/root/' + 'jev_' + selected['decision_id']
        hook.codex_event(self.project, {**payload, 'hook_event_name': 'PostToolUse', 'tool_response': {'task_name': child}})
        hook.codex_event(self.project, {'hook_event_name': 'SubagentStart', 'session_id': 'root',
            'agent_id': child, 'agent_type': 'developer', 'model': 'fast'})
        record = json.loads((self.project / '.agentic/jev' / ('prepared-' + selected['decision_id'] + '.json')).read_text())
        self.assertEqual(record['observed_model'], 'fast')
        self.assertTrue(test_blackbox.blackbox.codex_prepared_application(self.project, self.fixture.records(), 'root', {self.task}))

    def test_disabled_cli_is_local_and_has_no_registry(self):
        (self.project / '.agentic.json').write_text('{"settings":{"jev":{"enabled":false}}}')
        result = subprocess.run([sys.executable, str(Path(hook.__file__)), '--host', 'codex', '--project-dir', str(self.project), '--prepare-spawn'],
            input='{}', text=True, capture_output=True, check=True, env={'PYTHONDONTWRITEBYTECODE': '1'})
        self.assertEqual(json.loads(result.stdout)['reason_code'], 'disabled')

    def test_changed_profile_policy_blocks_stale_unique_launch(self):
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.fixture.answer(r, 'fast')):
            selected = self.prepare()
        (self.project / '.codex/agents/developer.toml').write_text('sandbox_mode = "read-only"\n')
        result = hook.codex_event(self.project, self.payload(selected))
        self.assertEqual(result['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_expired_and_reused_tickets_do_not_execute_as_native_pins(self):
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.fixture.answer(r, 'fast')):
            selected = self.prepare()
        first = self.payload(selected)
        self.assertEqual(hook.codex_event(self.project, first), {})
        reused = hook.codex_event(self.project, self.payload(selected, 'different-tool'))
        self.assertEqual(reused['hookSpecificOutput']['permissionDecision'], 'deny')
        with patch.object(prepared.time, 'time', return_value=selected['expires_at'] + 1):
            expired = hook.codex_event(self.project, first)
        self.assertEqual(expired['hookSpecificOutput']['permissionDecision'], 'deny')

    def policy_profile(self):
        (self.project / '.codex/agents/developer.toml').write_text(
            'description = "Developer"\nsandbox_mode = "workspace-write"\ndeveloper_instructions = "Stay in scope."\n')

    def test_response_has_one_authoritative_spawn_location(self):
        # Regression: the calculator session copied a top-level `task_name` that disagreed with `spawn`.
        self.policy_profile()
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.fixture.answer(r, 'fast')):
            selected = self.prepare()
        self.assertNotIn('task_name', selected)
        self.assertEqual(selected['spawn'], {'agent_type': 'developer', 'task_name': 'jev_' + selected['decision_id'],
                                             'model': 'fast', 'fork_turns': 'none'})
        self.assertEqual(selected['on_reject'], 'native_default_report')

    def test_policy_profile_keeps_recommendation_through_native_spawn(self):
        self.policy_profile()
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.fixture.answer(r, 'fast')):
            selected = self.prepare()
        payload = self.payload(selected)
        self.assertEqual(hook.codex_event(self.project, payload), {})
        child = '/root/' + selected['spawn']['task_name']
        hook.codex_event(self.project, {**payload, 'hook_event_name': 'PostToolUse', 'tool_response': {'task_name': child}})
        hook.codex_event(self.project, {'hook_event_name': 'SubagentStart', 'session_id': 'root',
            'agent_id': child, 'agent_type': 'developer', 'model': 'fast'})
        record = json.loads((self.project / '.agentic/jev' / ('prepared-' + selected['decision_id'] + '.json')).read_text())
        self.assertEqual((record['submitted_model'], record['observed_model']), ('fast', 'fast'))
        self.assertEqual(record['correlation_status'], 'native_child_bound')
        self.assertTrue(test_blackbox.blackbox.codex_prepared_application(self.project, self.fixture.records(), 'root', {self.task}))

    def test_wrong_or_missing_agent_type_is_rejected(self):
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.fixture.answer(r, 'fast')):
            selected = self.prepare()
        for agent_type in ('qa', None):
            payload = self.payload(selected, 'tool-' + str(agent_type))
            payload['tool_input'] = {key: value for key, value in {**payload['tool_input'], 'agent_type': agent_type}.items() if value}
            result = hook.codex_event(self.project, payload)
            self.assertEqual(result['hookSpecificOutput']['permissionDecision'], 'deny')
            self.assertIn('prepared_agent_type_mismatch', result['hookSpecificOutput']['permissionDecisionReason'])

    def test_rejected_launch_reports_discarded_recommendation(self):
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.fixture.answer(r, 'fast')):
            selected = self.prepare()
        hook.codex_event(self.project, self.payload(selected))
        denied = hook.codex_event(self.project, self.payload(selected, 'different-tool'))
        reason = denied['hookSpecificOutput']['permissionDecisionReason']
        self.assertIn('prepared_already_claimed', reason)
        self.assertIn('recommendation_discarded', reason)
        self.assertIn('do not retry', reason)
        discarded = [r for r in self.fixture.records('spawn') if r['outcome'] == 'recommendation_discarded']
        self.assertEqual([r['result']['reason_code'] for r in discarded], ['prepared_already_claimed'])

    def test_native_pin_is_not_resubmitted_as_override(self):
        (self.project / '.codex/agents/developer.toml').write_text('description = "Developer"\nmodel = "balanced"\n')
        selected = self.prepare()
        self.assertEqual(selected['model_source'], 'user_pin')
        self.assertNotIn('model', selected['spawn'])
        self.assertEqual(hook.codex_event(self.project, self.payload(selected)), {})
        record = json.loads((self.project / '.agentic/jev' / ('prepared-' + selected['decision_id'] + '.json')).read_text())
        self.assertEqual((record['submitted_model'], record['application_status']), (None, 'submitted_unconfirmed'))

    def test_parallel_policy_profile_launches_bind_only_their_own_child(self):
        self.policy_profile()
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.fixture.answer(r, 'fast')):
            first, second = self.prepare('one'), self.prepare('two')
        launches = ((first, 'first'), (second, 'second'))
        for selected, tool in launches:
            hook.codex_event(self.project, self.payload(selected, tool))
        # Native observations arrive before and out of order with spawn responses.
        for selected, _ in reversed(launches):
            hook.codex_event(self.project, {'hook_event_name': 'SubagentStart', 'session_id': 'root',
                'agent_id': '/root/' + selected['spawn']['task_name'], 'agent_type': 'developer', 'model': 'fast'})
        for selected, tool in launches:
            hook.codex_event(self.project, {**self.payload(selected, tool), 'hook_event_name': 'PostToolUse',
                'tool_response': {'task_name': '/root/' + selected['spawn']['task_name']}})
        for selected, tool in launches:
            record = json.loads((self.project / '.agentic/jev' / ('prepared-' + selected['decision_id'] + '.json')).read_text())
            self.assertEqual((record['tool_use_id'], record['child_task_name']), (tool, '/root/' + selected['spawn']['task_name']))
            self.assertEqual(record['application_status'], 'observed')

    def native_child(self, selected, thread='01a158b3-fef3-7960-9753-486d78dedbbe', meta_id=None):
        """Native shape (Codex 0.163.0): SubagentStart.agent_id is a thread id; its transcript names the canonical path."""
        transcript = self.project / ('child-' + thread + '.jsonl')
        meta = {'type': 'session_meta', 'payload': {'id': meta_id or thread, 'agent_role': 'developer',
                'agent_path': '/root/' + selected['spawn']['task_name']}}
        transcript.write_text(json.dumps(meta) + '\n' + json.dumps({'type': 'turn_context'}) + '\n')
        return {'hook_event_name': 'SubagentStart', 'session_id': 'root', 'agent_id': thread,
                'agent_type': 'developer', 'model': 'fast', 'transcript_path': str(transcript)}

    def record(self, selected):
        return json.loads((self.project / '.agentic/jev' / ('prepared-' + selected['decision_id'] + '.json')).read_text())

    def test_spawn_name_matches_native_agent_name_rule(self):
        # Native rejection: "agent_name must use only lowercase letters, digits, and underscores".
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.fixture.answer(r, 'fast')):
            selected = self.prepare()
        self.assertRegex(selected['spawn']['task_name'], r'^[a-z0-9_]+$')

    def test_thread_id_observation_binds_through_its_own_transcript(self):
        self.policy_profile()
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.fixture.answer(r, 'fast')):
            selected = self.prepare()
        payload = self.payload(selected)
        hook.codex_event(self.project, payload)
        hook.codex_event(self.project, self.native_child(selected))
        hook.codex_event(self.project, {**payload, 'hook_event_name': 'PostToolUse',
            'tool_response': {'task_name': '/root/' + selected['spawn']['task_name']}})
        self.assertEqual((self.record(selected)['observed_model'], self.record(selected)['application_status']), ('fast', 'observed'))
        self.assertTrue(test_blackbox.blackbox.codex_prepared_application(self.project, self.fixture.records(), 'root', {self.task}))

    def test_foreign_or_missing_transcript_keeps_observation_unbound(self):
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.fixture.answer(r, 'fast')):
            selected = self.prepare()
        payload = self.payload(selected)
        hook.codex_event(self.project, payload)
        hook.codex_event(self.project, {**payload, 'hook_event_name': 'PostToolUse',
            'tool_response': {'task_name': '/root/' + selected['spawn']['task_name']}})
        parent = self.native_child(selected, meta_id='parent-thread')
        missing = {**self.native_child(selected, thread='other-thread'), 'transcript_path': str(self.project / 'absent.jsonl')}
        for start in (parent, missing, {key: value for key, value in parent.items() if key != 'transcript_path'}):
            hook.codex_event(self.project, start)
        self.assertEqual((self.record(selected)['observed_model'], self.record(selected)['application_status']), (None, 'submitted_unconfirmed'))

    def test_host_rejected_spawn_never_becomes_observed(self):
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.fixture.answer(r, 'fast')):
            selected = self.prepare()
        payload = self.payload(selected)
        hook.codex_event(self.project, payload)
        hook.codex_event(self.project, {**payload, 'hook_event_name': 'PostToolUse',
            'tool_response': 'agent_name must use only lowercase letters, digits, and underscores'})
        record = self.record(selected)
        self.assertEqual((record['application_status'], record.get('child_task_name')), ('submitted_unconfirmed', None))
        self.assertFalse(test_blackbox.blackbox.codex_prepared_application(self.project, self.fixture.records(), 'root', {self.task}))

    def test_native_string_spawn_response_promotes_pending_observation(self):
        self.policy_profile()
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.fixture.answer(r, 'fast')):
            selected = self.prepare()
        payload = self.payload(selected)
        hook.codex_event(self.project, payload)
        hook.codex_event(self.project, self.native_child(selected))
        response = json.dumps({'task_name': '/root/' + selected['spawn']['task_name']})
        hook.codex_event(self.project, {**payload, 'hook_event_name': 'PostToolUse', 'tool_response': response})
        record = self.record(selected)
        self.assertEqual((record['observed_model'], record['correlation_status']), ('fast', 'native_child_bound'))
        self.assertNotIn('pending_observation', record)
        self.assertTrue(test_blackbox.blackbox.codex_prepared_application(self.project, self.fixture.records(), 'root', {self.task}))
