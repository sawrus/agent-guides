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
        child = '/root/' + selected['task_name']
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
