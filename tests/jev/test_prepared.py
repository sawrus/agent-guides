"""Prepared Codex decisions: synthetic assignments, no model/network calls."""
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading
import tempfile
import unittest
from unittest.mock import patch
import hook
import prepared


class Prepared(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        (self.project / '.agentic.json').write_text('{"settings":{"jev":{"enabled":true}}}')
        self.directory = hook.private_dir(self.project)
        self.context_path = self.directory / ('context-' + hook.short_hash('session') + '.json')
        hook.save_json(self.context_path, {'task_id': 'task', 'generation': 'gen', 'jev': 'on'})
        self.payload = dict(session_id='session', task_id='task', request_id='request', role='developer',
                            goal='Implement CLI', scope='Only calc.py', complexity='Four operations and invalid input')
        profile = self.project / '.codex/agents/developer.toml'
        profile.parent.mkdir(parents=True, exist_ok=True)
        profile.write_text('description = "Developer"\n')
        self.models = patch.object(hook, 'codex_models', return_value=[{'id': 'fast'}, {'id': 'strong'}])
        self.models.start()
        self.native_run = hook.run_event
        self.runtime = patch.object(hook, 'run_event', return_value={'status': 'evaluated', 'model': 'strong', 'model_source': 'jev_tier'})
        self.call = self.runtime.start()

    def tearDown(self):
        self.runtime.stop()
        self.models.stop()
        self.tmp.cleanup()

    def prepare(self, **values):
        return prepared.prepare(hook, self.project, {**self.payload, **values})

    def claim(self, decision, **values):
        return prepared.claim(hook, self.project, dict(session_id='session', task_id='task',
            task_name='jev_' + decision['decision_id'], agent_type='developer', tool_use_id='tool-1', model='strong', fork_turns='none', **values))

    def test_open_assignment_is_used_and_retry_is_free(self):
        result = self.prepare()
        self.assertEqual(result['recommended_model'], 'strong')
        self.assertEqual(result['spawn']['fork_turns'], 'none')
        self.assertEqual(self.prepare()['decision_id'], result['decision_id'])
        self.assertEqual(self.call.call_count, 1)
        prompt = self.call.call_args.args[1]['prompt']
        self.assertIn('Implement CLI', prompt)
        self.assertIn('Only calc.py', prompt)
        self.assertIn('Four operations', prompt)
        self.assertEqual(result['observed_model'], None)

    def test_parallel_same_role_is_not_crossed(self):
        a, b = self.prepare(), self.prepare(request_id='second', goal='Different goal')
        self.assertNotEqual('jev_' + a['decision_id'], 'jev_' + b['decision_id'])
        self.assertEqual(self.claim(a)['decision_id'], a['decision_id'])
        self.assertEqual(self.claim(b)['decision_id'], b['decision_id'])

    def test_consumed_decision_retry_same_tool_only(self):
        result = self.prepare()
        self.assertEqual(self.claim(result)['submitted_model'], 'strong')
        self.assertEqual(self.claim(result)['decision_id'], result['decision_id'])
        other = dict(session_id='session', task_id='task', task_name='jev_' + result['decision_id'], tool_use_id='other', model='strong', fork_turns='none')
        self.assertEqual(prepared.claim(hook, self.project, other)['reason_code'], 'prepared_already_claimed')

    def test_expiry_and_new_task_are_rejected(self):
        result = self.prepare()
        with patch.object(prepared.time, 'time', return_value=result['expires_at'] + 1):
            self.assertEqual(self.claim(result)['reason_code'], 'prepared_expired')
        hook.save_json(self.context_path, {'task_id': 'new', 'generation': 'next', 'jev': 'on'})
        self.assertEqual(self.claim(result)['reason_code'], 'prepared_task_mismatch')

    def test_request_mutation_rejected(self):
        self.prepare()
        self.assertEqual(self.prepare(goal='other')['reason_code'], 'prepared_request_conflict')
        self.assertEqual(self.call.call_count, 1)

    def test_profile_pin_wins_without_jev(self):
        profile = self.project / '.codex/agents/developer.toml'
        profile.parent.mkdir(parents=True, exist_ok=True)
        profile.write_text('model = "fast"\n')
        result = self.prepare()
        self.assertEqual(result['recommended_model'], 'fast')
        self.assertEqual(result['model_source'], 'user_pin')
        self.call.assert_not_called()

    def test_pin_added_after_prepare_prevents_recommendation_application(self):
        result = self.prepare()
        profile = self.project / '.codex/agents/developer.toml'
        profile.parent.mkdir(parents=True, exist_ok=True)
        profile.write_text('model = "fast"\n')
        claim = self.claim(result)
        self.assertEqual(claim['reason_code'], 'profile_pin_changed')
        self.assertIsNone(claim['observed_model'])

    def test_timeout_retry_does_not_call_again(self):
        self.call.side_effect = TimeoutError('synthetic')
        self.assertEqual(self.prepare()['status'], 'fallback')
        self.assertEqual(self.prepare()['status'], 'fallback')
        self.assertEqual(self.call.call_count, 1)

    def test_unknown_model_and_low_confidence_fallback(self):
        for result in ({'status': 'evaluated', 'model': 'unknown'},
                       {'status': 'fallback', 'reason_code': 'low_confidence'}):
            self.call.return_value = result
            response = self.prepare(request_id=str(result))
            self.assertNotIn('spawn', response)

    def test_disabled_and_missing_metadata_no_call(self):
        self.assertEqual(prepared.claim(hook, self.project, {})['status'], 'fallback')
        (self.project / '.agentic.json').write_text('{"settings":{"jev":{"enabled":false}}}')
        with patch.object(hook, 'scrub', side_effect=AssertionError('credentials read')):
            self.assertEqual(self.prepare()['reason_code'], 'disabled')
        self.call.assert_not_called()

    def test_redacted_and_size_limited_assignment(self):
        self.prepare(goal='Fix password=syntheticvalue')
        self.assertNotIn('syntheticvalue', json.dumps(self.call.call_args.args, default=str))
        self.assertEqual(self.prepare(request_id='large', goal='x' * 40000)['reason_code'], 'prepared_input_too_large')

    def test_observation_requires_exact_binding(self):
        result = self.prepare()
        self.claim(result)
        base = dict(session_id='session', task_id='task', task_name='jev_' + result['decision_id'], tool_use_id='tool-1')
        self.assertEqual(prepared.observe(hook, self.project, {**base, 'observed_model': 'strong'})['observed_model'], 'strong')
        self.assertEqual(prepared.observe(hook, self.project, {**base, 'tool_use_id': 'wrong', 'observed_model': 'fast'})['status'], 'fallback')

    def test_low_confidence_returns_explicit_role_default(self):
        self.call.return_value = {'status': 'fallback', 'reason_code': 'low_confidence', 'model': 'fast', 'model_source': 'role_default'}
        result = self.prepare()
        self.assertEqual(result['spawn']['model'], 'fast')
        self.assertEqual(result['model_source'], 'role_default')
        self.assertEqual(result['reason_code'], 'low_confidence')

    def test_session_off_does_not_scrub_or_call(self):
        hook.save_json(self.context_path, {'task_id': 'task', 'generation': 'gen', 'jev': 'off'})
        with patch.object(hook, 'scrub', side_effect=AssertionError('credentials read')):
            self.assertEqual(self.prepare()['reason_code'], 'prepared_task_mismatch')
        self.call.assert_not_called()

    def test_pending_record_does_not_repeat_after_crash(self):
        original = hook.save_json
        def interrupted(path, data):
            if path.name.startswith('prepared-') and data.get('status') == 'prepared':
                raise OSError('synthetic crash after request')
            return original(path, data)
        with patch.object(hook, 'save_json', side_effect=interrupted):
            with self.assertRaises(OSError):
                self.prepare()
        self.assertEqual(self.prepare()['reason_code'], 'prepared_incomplete')
        self.assertEqual(self.call.call_count, 1)

    def test_availability_checked_again_at_claim(self):
        result = self.prepare()
        hook.save_json(self.directory / 'availability.json', {'codex:strong': result['expires_at']})
        self.assertEqual(self.claim(result)['reason_code'], 'prepared_model_unavailable')

    def test_parallel_request_retry_calls_once(self):
        entered, release = threading.Event(), threading.Event()
        def evaluate(*args):
            entered.set()
            release.wait(0.1)
            return {'status': 'evaluated', 'model': 'strong'}
        self.call.side_effect = evaluate
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(self.prepare)
            self.assertTrue(entered.wait(1))
            second = executor.submit(self.prepare)
            release.set()
            self.assertEqual(first.result()['decision_id'], second.result()['decision_id'])
        self.assertEqual(self.call.call_count, 1)

    def test_uninstalled_role_is_not_routed(self):
        self.assertEqual(self.prepare(role='invented')['reason_code'], 'prepared_role_unavailable')
        self.call.assert_not_called()

    def test_metadata_symlinks_rejected(self):
        result = self.prepare()
        path = self.directory / ('prepared-' + result['decision_id'] + '.json')
        target = self.project / 'redirect.json'
        target.write_text(path.read_text())
        path.unlink()
        path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'redirected prepared'):
            self.prepare()
        with self.assertRaisesRegex(ValueError, 'redirected prepared'):
            self.claim(result)

    def test_native_child_link_is_exact_and_observation_order_matters(self):
        result = self.prepare()
        self.claim(result)
        child = '/root/' + 'jev_' + result['decision_id']
        event = dict(session_id='session', task_id='task', child_session_id=child, observed_model='strong')
        self.assertEqual(prepared.observe_child(hook, self.project, event)['reason_code'], 'prepared_child_unbound')
        link = dict(session_id='session', task_id='task', task_name='jev_' + result['decision_id'], tool_use_id='tool-1', child_session_id=child)
        self.assertEqual(prepared.link_child(hook, self.project, link)['observed_model'], 'strong')
        observed = prepared.observe_child(hook, self.project, event)
        self.assertEqual(observed['observed_model'], 'strong')
        self.assertEqual(observed['application_status'], 'observed')
        self.assertEqual(prepared.observe_child(hook, self.project, {**event, 'child_session_id': '/other/' + 'jev_' + result['decision_id']})['reason_code'], 'prepared_child_unbound')
        self.assertEqual(prepared.link_child(hook, self.project, {**link, 'child_session_id': '/root/other'})['reason_code'], 'prepared_child_unbound')

    def test_real_runtime_prepares_before_encrypted_native_spawn(self):
        self.runtime.stop()
        defaults = self.project / '.agent/jev/model-defaults.json'
        defaults.parent.mkdir(parents=True)
        defaults.write_text(json.dumps({'version': 2, 'roles': {'developer': 'fast'}, 'tiers': {'fast': 'fast', 'frontier': 'strong'}}))
        def answer(project, settings, request):
            self.assertIn('Implement CLI', request['state']['assignment'])
            self.assertIn('Only calc.py', request['state']['assignment'])
            self.assertFalse(request['state']['assignment_unavailable'])
            return {'status': 'evaluated', 'answers': {'model': {'choice': 'frontier', 'confidence': 1}}, 'usage': {'input_tokens': 10, 'output_tokens': 1}}
        with patch.object(hook, 'evaluate', side_effect=answer) as network:
            result = self.prepare()
            payload = {'hook_event_name': 'PreToolUse', 'session_id': 'session', 'tool_use_id': 'tool-native',
                       'tool_name': 'spawn_agent', 'tool_input': {**result['spawn'], 'message': hook.adapters.CODEX_ENCRYPTED_PREFIX + 'synthetic-opaque'}}
            self.assertEqual(hook.adapters.codex_event(hook, self.project, payload), {})
            self.assertEqual(network.call_count, 1)
            record = hook.read_json(self.directory / ('prepared-' + result['decision_id'] + '.json'))
            self.assertEqual(record['submitted_model'], 'strong')
            self.assertIsNone(record['observed_model'])
            logs = [hook.read_json(path) for path in self.directory.glob('event-*.json')]
            prepared_log = next(log for log in logs if log['context'].get('preparation_only'))
            self.assertFalse(prepared_log['applied'])
            self.assertEqual(prepared_log['outcome'], 'recommended_unconfirmed')
            child = '/root/' + 'jev_' + result['decision_id']
            hook.adapters.codex_event(hook, self.project, {'hook_event_name': 'SubagentStart', 'session_id': 'session', 'agent_id': child, 'model': 'strong'})
            early = hook.read_json(self.directory / ('prepared-' + result['decision_id'] + '.json'))
            self.assertIsNone(early['observed_model'])
            hook.adapters.codex_event(hook, self.project, {**payload, 'hook_event_name': 'PostToolUse', 'tool_response': {'task_name': child}})
            observed = hook.read_json(self.directory / ('prepared-' + result['decision_id'] + '.json'))
            self.assertEqual(observed['observed_model'], 'strong')
            self.assertEqual(network.call_count, 1)

    def test_native_profile_policy_is_preserved_through_agent_type(self):
        profile = self.project / '.codex/agents/developer.toml'
        profile.write_text('description = "Developer"\nsandbox_mode = "read-only"\n')
        result = self.prepare()
        self.assertEqual(result['spawn']['agent_type'], 'developer')
        self.assertEqual(result['spawn']['task_name'], 'jev_' + result['decision_id'])
        self.assertEqual(result['spawn']['model'], 'strong')
        self.assertEqual(result['correlation_status'], 'awaiting_native_binding')
        self.assertEqual(result['application_status'], 'unconfirmed')
        self.assertEqual(self.claim(result)['correlation_status'], 'submission_bound')
        self.assertIsNone(result['observed_model'])
        self.assertEqual(profile.read_text(), 'description = "Developer"\nsandbox_mode = "read-only"\n')

    def test_consumed_request_does_not_return_reusable_spawn(self):
        result = self.prepare()
        self.claim(result)
        self.assertNotIn('spawn', self.prepare())
        self.assertEqual(self.call.call_count, 1)

    def test_each_assignment_field_survives_size_bounding(self):
        self.prepare(goal='g' * 4000, scope='SCOPE-MARKER' + 's' * 4000, complexity='COMPLEXITY-MARKER' + 'c' * 4000)
        assignment = self.call.call_args.args[1]['prompt']
        self.assertLessEqual(len(assignment), hook.questions.ASSIGNMENT_LIMIT)
        self.assertIn('SCOPE-MARKER', assignment)
        self.assertIn('COMPLEXITY-MARKER', assignment)
        self.assertIn('[truncated]', assignment)

    def test_task_reset_during_evaluation_returns_no_spawn(self):
        def reset(*args):
            hook.save_json(self.context_path, {'task_id': 'new', 'generation': 'next', 'jev': 'on'})
            return {'status': 'evaluated', 'model': 'strong', 'model_source': 'jev_tier'}
        self.call.side_effect = reset
        result = self.prepare()
        self.assertEqual(result['reason_code'], 'prepared_task_mismatch')
        self.assertNotIn('spawn', result)

    def test_task_reset_during_cached_read_returns_no_spawn(self):
        initial = self.prepare()
        original = prepared.read_record
        def reset_on_record(core, path):
            value = original(core, path)
            if path.name == 'prepared-' + initial['decision_id'] + '.json':
                hook.save_json(self.context_path, {'task_id': 'new', 'generation': 'next', 'jev': 'on'})
            return value
        with patch.object(prepared, 'read_record', side_effect=reset_on_record):
            result = self.prepare()
        self.assertEqual(result['reason_code'], 'prepared_task_mismatch')
        self.assertNotIn('spawn', result)
        self.assertEqual(self.call.call_count, 1)

    def test_native_instructions_and_effort_keep_canonical_profile(self):
        profile = self.project / '.codex/agents/developer.toml'
        for setting in ('developer_instructions = "Only read files"', 'model_reasoning_effort = "high"'):
            profile.write_text(setting + '\n')
            result = self.prepare(request_id=setting)
            self.assertEqual(result['spawn']['agent_type'], 'developer')
            self.assertEqual(result['correlation_status'], 'awaiting_native_binding')
            self.assertIsNone(result['observed_model'])

    def test_instruction_example_is_not_a_model_pin(self):
        if prepared.tomllib is None:
            self.skipTest('TOML parser unavailable')
        profile = self.project / '.codex/agents/developer.toml'
        profile.write_text("developer_instructions = " + "'" * 3 + "\nExample:\nmodel = \"fast\"\n" + "'" * 3 + "\n")
        result = self.prepare()
        self.assertEqual(result['model_source'], 'jev_tier')
        self.assertEqual(result['recommended_model'], 'strong')
        self.assertEqual(self.call.call_count, 1)
        self.assertEqual(result['spawn']['agent_type'], 'developer')

    def test_python310_rejects_ambiguous_profiles_and_keeps_simple_pin(self):
        profile = self.project / '.codex/agents/developer.toml'
        with patch.object(prepared, 'tomllib', None):
            profile.write_text('model = "fast" # user pin\n')
            self.assertEqual(self.prepare()['model_source'], 'user_pin')
            profile.write_text("developer_instructions = " + "'" * 3 + "\nmodel = \"fast\"\n" + "'" * 3 + "\n")
            result = self.prepare(request_id='multiline')
            self.assertEqual(result['status'], 'fallback')
            self.assertNotIn('spawn', result)
            profile.write_text('model = "fast"\nmodel = "strong"\n')
            self.assertNotIn('spawn', self.prepare(request_id='duplicate'))
        self.call.assert_not_called()

    def test_profile_changes_during_evaluation_return_no_spawn(self):
        profile = self.project / '.codex/agents/developer.toml'
        for setting, reason in (('model = "fast"', 'profile_pin_changed'),
                                ('developer_instructions = "Read only"', 'profile_policy_changed')):
            profile.write_text('description = "Developer"\n')
            def changed(*args):
                profile.write_text(setting + '\n')
                return {'status': 'evaluated', 'model': 'strong', 'model_source': 'jev_tier'}
            self.call.side_effect = changed
            result = self.prepare(request_id=setting)
            self.assertEqual(result['reason_code'], reason)
            self.assertNotIn('spawn', result)

    def test_cached_recommendation_rechecks_current_profile(self):
        profile = self.project / '.codex/agents/developer.toml'
        for setting, reason in (('model = "fast"', 'profile_pin_changed'),
                                ('sandbox_mode = "read-only"', 'profile_policy_changed')):
            profile.write_text('description = "Developer"\n')
            self.prepare(request_id=setting)
            profile.write_text(setting + '\n')
            result = self.prepare(request_id=setting)
            self.assertEqual(result['reason_code'], reason)
            self.assertNotIn('spawn', result)
        self.assertEqual(self.call.call_count, 2)

    def test_pending_observation_promotes_only_after_exact_native_response(self):
        result = self.prepare()
        self.claim(result)
        child = '/root/' + 'jev_' + result['decision_id']
        event = dict(session_id='session', task_id='task', child_session_id=child, observed_model='strong')
        early = prepared.observe_child(hook, self.project, event)
        self.assertIsNone(early['observed_model'])
        path = self.directory / ('prepared-' + result['decision_id'] + '.json')
        pending = hook.read_json(path)
        self.assertIsNone(pending['observed_model'])
        self.assertEqual(pending['pending_observation']['observed_model'], 'strong')
        link = dict(session_id='session', task_id='task', task_name='jev_' + result['decision_id'], tool_use_id='tool-1', child_session_id=child)
        promoted = prepared.link_child(hook, self.project, link)
        self.assertEqual(promoted['observed_model'], 'strong')
        self.assertEqual(promoted['application_status'], 'observed')
        self.assertNotIn('pending_observation', hook.read_json(path))

    def test_pending_wrong_child_and_conflicting_models_are_unconfirmed(self):
        for other in ('different-child', 'different-model'):
            result = self.prepare(request_id=other)
            self.claim(result)
            child = '/root/' + 'jev_' + result['decision_id']
            event = dict(session_id='session', task_id='task', child_session_id=child, observed_model='strong')
            prepared.observe_child(hook, self.project, event)
            conflict = {**event, 'observed_model': 'fast'} if other == 'different-model' else {**event, 'child_session_id': '/other/' + 'jev_' + result['decision_id']}
            self.assertEqual(prepared.observe_child(hook, self.project, conflict)['reason_code'], 'prepared_observation_conflict')
            linked = prepared.link_child(hook, self.project, dict(session_id='session', task_id='task', task_name='jev_' + result['decision_id'], tool_use_id='tool-1', child_session_id=child))
            self.assertIsNone(linked['observed_model'])
            self.assertEqual(linked['application_status'], 'unconfirmed')

    def test_pending_observation_rejects_expiry_and_new_task(self):
        result = self.prepare()
        self.claim(result)
        event = dict(session_id='session', task_id='task', child_session_id='/root/' + 'jev_' + result['decision_id'], observed_model='strong')
        with patch.object(prepared.time, 'time', return_value=result['expires_at'] + 1):
            self.assertEqual(prepared.observe_child(hook, self.project, event)['reason_code'], 'prepared_expired')
        hook.save_json(self.context_path, {'task_id': 'new', 'generation': 'next', 'jev': 'on'})
        self.assertEqual(prepared.observe_child(hook, self.project, event)['reason_code'], 'prepared_task_mismatch')

    def test_single_wrong_pending_child_is_not_promoted_by_response(self):
        result = self.prepare()
        self.claim(result)
        wrong = '/wrong-parent/' + 'jev_' + result['decision_id']
        prepared.observe_child(hook, self.project, dict(session_id='session', task_id='task', child_session_id=wrong, observed_model='strong'))
        linked = prepared.link_child(hook, self.project, dict(session_id='session', task_id='task', task_name='jev_' + result['decision_id'], tool_use_id='tool-1', child_session_id='/root/' + 'jev_' + result['decision_id']))
        self.assertIsNone(linked['observed_model'])
        self.assertEqual(linked['correlation_status'], 'observation_conflict')


class PreparedMetadataShapes(unittest.TestCase):
    setUp, tearDown, prepare = Prepared.setUp, Prepared.tearDown, Prepared.prepare

    def test_list_scope_from_native_coordinator_is_accepted(self):
        # Native regression (Codex 0.163.0): the coordinator sent "scope": ["hello.py"].
        result = self.prepare(scope=['hello.py', 'tests/'], goal='Create hello.py')
        self.assertEqual(result['status'], 'prepared')
        self.assertIn('hello.py; tests/', self.call.call_args.args[1]['prompt'])

    def test_non_text_metadata_is_reported_as_invalid(self):
        self.assertEqual(self.prepare(scope={'files': 1})['reason_code'], 'prepared_metadata_invalid')
        self.assertEqual(self.prepare(request_id='r2', scope=[])['reason_code'], 'prepared_metadata_missing')
        self.call.assert_not_called()
