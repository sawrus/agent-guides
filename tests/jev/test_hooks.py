"""Native hook contracts: routing, failover, redaction, dedup and permission boundaries."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import hook


class Hooks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        (self.project / '.agentic.json').write_text(json.dumps({'settings': {'jev': {'enabled': True}}}))
        workflows = self.project / '.agent/workflows'
        workflows.mkdir(parents=True)
        for name, desc in [('develop-feature', 'Implement a small backend feature'), ('code-review', 'Review existing code')]:
            (workflows / (name + '.md')).write_text(f'---\nname: {name}\ntrigger: /{name}\ndescription: {desc}\nagent: product-owner\n---\n')

    def tearDown(self):
        self.environment.stop()
        self.temp.cleanup()

    def answer(self, request, selected, confidence=1):
        name, question = next(iter(request['questions'].items()))
        return {'status': 'evaluated', 'answers': {name: {'type': 'choice', 'choice': selected, 'confidence': confidence,
                'probabilities': {k: int(k == selected) for k in question['criteria']}}}, 'usage': {'cost_usd': .0001}}

    def event(self, kind, **kwargs):
        return {'host': 'opencode', 'kind': kind, 'session_id': 'root', 'event_id': 'first', **kwargs}

    def test_off_does_not_read_keys_write_logs_or_call_network(self):
        (self.project / '.agentic.json').write_text('{"settings":{"jev":{"enabled":false}}}')
        with patch.object(hook, 'key_for', side_effect=AssertionError('key read')), patch.object(hook, 'evaluate', side_effect=AssertionError('network')):
            self.assertEqual(hook.run_event(self.project, self.event('prompt'))['reason_code'], 'disabled')
        self.assertFalse((self.project / '.agentic/jev').exists())

    def test_codex_catalog_uses_only_profile_default_models_and_user_pins(self):
        home = self.project / 'codex-home'
        home.mkdir()
        (home / 'models_cache.json').write_text(json.dumps({'models': [
            {'slug': name, 'visibility': 'list'} for name in ('light', 'default', 'user-pin', 'unrelated-expensive')]}))
        runtime = self.project / '.agent/jev'
        runtime.mkdir(parents=True)
        (runtime / 'model-defaults.json').write_text('{"developer":"default","qa":"light"}')
        profiles = self.project / '.codex/agents'
        profiles.mkdir(parents=True)
        (profiles / 'custom.toml').write_text('model = "user-pin"\n')
        with patch.dict(os.environ, {'CODEX_HOME': str(home)}):
            self.assertEqual({m['id'] for m in hook.codex_models(self.project)}, {'light', 'default', 'user-pin'})

    def test_codex_child_inherits_original_task_for_nested_routing(self):
        root = self.event('prompt', host='codex', prompt='/develop-feature build calculator')
        hook.run_event(self.project, root)
        hook.run_event(self.project, self.event('observation', host='codex', child_session_id='child', observed_model='light'))
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'local/light')):
            event = self.event('spawn', session_id='child', models=[{'id':'local/light'}, {'id':'local/heavy'}])
            hook.run_event(self.project, event)
        self.assertEqual(event['session_id'], 'child')
        records = [json.loads(p.read_text()) for p in (self.project / '.agentic/jev').glob('event-*.json')]
        child = next(r for r in records if r['context']['kind'] == 'spawn')
        self.assertEqual(child['context']['original_prompt'], root['prompt'])

    def test_reviewer_ciphertext_is_unchanged_and_receives_only_current_task_packet(self):
        hook.run_event(self.project, self.event('prompt', prompt='/develop-feature calculator'))
        hook.run_event(self.project, self.event('prompt', session_id='other', event_id='other-task', prompt='/code-review unrelated'))
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'light')):
            hook.run_event(self.project, self.event('spawn', event_id='developer', agent='developer', models=[{'id':'light'}, {'id':'heavy'}]))
        ciphertext = 'gAAAA-opaque-assignment'
        payload = {'hook_event_name':'PreToolUse', 'session_id':'root', 'tool_use_id':'reviewer',
                   'tool_name':'spawn_agent', 'tool_input':{'agent_type':'instruction_reviewer', 'message':ciphertext}}
        with patch.object(hook, 'codex_models', return_value=[{'id':'gpt-6-luna'}, {'id':'heavy'}]):
            result = hook.codex_event(self.project, payload)['hookSpecificOutput']
        self.assertEqual(result['updatedInput']['message'], ciphertext)
        start = hook.codex_event(self.project, {'hook_event_name':'SubagentStart', 'session_id':'root',
                 'agent_id':'review-child', 'agent_type':'instruction_reviewer', 'model':'gpt-6-luna'})
        self.assertIn('.agentic/jev/review-', start['hookSpecificOutput']['additionalContext'])
        packet = json.loads(next((self.project / '.agentic/jev').glob('review-*.json')).read_text())
        self.assertTrue(any(d['questions'] for d in packet['decisions']))
        for decision in packet['decisions']:
            record = json.loads((self.project / decision['record']).read_text())
            self.assertEqual(record['context']['task_id'], 'first')

    def test_opencode_review_packet_is_delivered_once_per_event_without_paid_review_call(self):
        hook.run_event(self.project, self.event('prompt', prompt='/develop-feature calculator'))
        event = self.event('spawn', event_id='reviewer', agent='instruction_reviewer', models=[{'id':'gpt-6-luna'}, {'id':'heavy'}])
        with patch.object(hook, 'evaluate', side_effect=AssertionError('paid review call')):
            result = hook.run_event(self.project, event)
            self.assertTrue((self.project / result['review_packet']).is_file())
            self.assertNotIn('review_packet', hook.run_event(self.project, event))
            handoff = hook.run_event(self.project, self.event('review_handoff', session_id='child', root_session_id='root', event_id='child-review', agent='instruction_reviewer'))
            self.assertEqual(handoff['review_packet'], result['review_packet'])

    def test_workflow_context_model_and_repeat_are_scoped(self):
        def respond(project, settings, request):
            return self.answer(request, 'develop-feature' if 'workflow' in request['questions'] else 'local/light')
        with patch.object(hook, 'evaluate', side_effect=respond) as api:
            event = self.event('prompt', prompt='разработай калькулятор')
            result = hook.run_event(self.project, event)
            self.assertEqual(result['workflow']['id'], 'develop-feature')
            self.assertEqual(hook.run_event(self.project, event), result)
            self.assertEqual(api.call_count, 1)
            models = [{'id': 'local/light', 'description': 'cheap coder'}, {'id': 'local/frontier', 'description': 'hard research'}]
            result = hook.run_event(self.project, self.event('spawn', event_id='spawn1', models=models, agent='developer', prompt='Implement 4 operations'))
            self.assertEqual(result['model'], 'local/light')
            self.assertIn('LEAST EXPENSIVE SUFFICIENT', api.call_args.args[2]['questions']['model']['instructions'])
            self.assertEqual(api.call_args.args[2]['state']['original_prompt'], 'разработай калькулятор')
            self.assertEqual(api.call_args.args[2]['state']['workflow']['id'], 'develop-feature')

    def test_explicit_workflow_and_models_are_preserved(self):
        with patch.object(hook, 'evaluate', side_effect=AssertionError('network')):
            result = hook.run_event(self.project, self.event('prompt', prompt='Follow /develop-feature'))
            self.assertEqual(result['status'], 'preserved')
            result = hook.run_event(self.project, self.event('spawn', models=[{'id': 'a'}, {'id': 'b'}], pinned_model='b'))
            self.assertEqual(result['status'], 'preserved')
            result = hook.run_event(self.project, self.event('spawn', event_id='continued', models=[{'id': 'a'}, {'id': 'b'}], continuation=True))
            self.assertEqual(result['status'], 'preserved')

    def test_low_confidence_and_http_failure_fall_back(self):
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'develop-feature', .8)):
            self.assertEqual(hook.run_event(self.project, self.event('prompt', prompt='Build API'))['reason_code'], 'low_confidence')
        with patch.object(hook, 'evaluate', side_effect=TimeoutError()):
            self.assertEqual(hook.run_event(self.project, self.event('prompt', event_id='second', prompt='Build API'))['reason_code'], 'request_failed')

    def test_full_qa_is_redacted_and_retained(self):
        (self.project / '.env').write_text('JEV_API_KEY=unusual-paid-key\n')
        def respond(project, settings, request):
            self.assertNotIn('unusual-paid-key', json.dumps(request))
            self.assertNotIn('plaintext-secret', json.dumps(request))
            return {**self.answer(request, 'develop-feature'), 'response': {'secret': 'plaintext-secret', 'detail': 'unusual-paid-key'}}
        with patch.object(hook, 'evaluate', side_effect=respond):
            hook.run_event(self.project, self.event('prompt', prompt='Build API. token=plaintext-secret key unusual-paid-key'))
        records = list((self.project / '.agentic/jev').glob('event-*.json'))
        text = records[0].read_text()
        self.assertNotIn('unusual-paid-key', text)
        self.assertNotIn('plaintext-secret', text)
        self.assertIn('questions', text)
        self.assertIn('response', text)
        os.utime(records[0], (0, 0))
        hook.private_dir(self.project)
        self.assertFalse(records[0].exists())

    def test_permission_limits_resist_even_confident_allow(self):
        base = self.event('permission', action='write', resources=[str(self.project / 'src.py')])
        self.assertTrue(hook.permission_boundaries(self.project, base))
        for event in [dict(base, resources=['/etc/config']), dict(base, resources=[str(self.project / '.env')]),
                      dict(base, action='delete'), dict(base, input={'sandbox_permissions': 'require_escalated'}),
                      dict(base, host='codex', action='Bash', input={'command': 'ls'})]:
            self.assertFalse(hook.permission_boundaries(self.project, event))
            with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'allow')):
                event['event_id'] = json.dumps(event)
                self.assertEqual(hook.run_event(self.project, event)['decision'], 'ask')
        self.assertTrue(hook.permission_boundaries(self.project, self.event('permission', action='bash', resources=['mkdir src'])))
        self.assertFalse(hook.permission_boundaries(self.project, self.event('permission', action='bash', resources=['python -c "open(\'/etc/config\',\'w\')"'])))
        self.assertFalse(hook.permission_boundaries(self.project, self.event('permission', action='bash', resources=['rm -rf src'])))
        self.assertFalse(hook.permission_boundaries(self.project, self.event('permission', action='bash', input={'command':'ls', 'workdir':'/etc'})))
        for command in ('wc --files0-from=/etc/secret', 'touch -rsecret-link output', 'ls -RL src'):
            self.assertFalse(hook.permission_boundaries(self.project, self.event('permission', action='bash', input={'command':command})))
        for target in ('/etc/config', ' .env', str(self.project / '.env')):
            patch_text = f'*** Update File: src.py\n*** Move to: {target}\n@@\n-old\n+new\n'
            self.assertFalse(hook.permission_boundaries(self.project, self.event('permission', action='apply_patch', input={'patchText': patch_text})))
        self.assertFalse(hook.permission_boundaries(self.project, dict(base, metadata={'sensitive': True})))
        self.assertFalse(hook.permission_boundaries(self.project, self.event('permission', action='apply_patch', input={'patchText': '*** Delete File: src.py'})))

    @unittest.skipUnless(hasattr(os, 'symlink'), 'symlinks unavailable')
    def test_symlink_escape_and_redirected_logs_are_rejected(self):
        link = self.project / 'escape'
        try:
            link.symlink_to('/etc', target_is_directory=True)
        except OSError:
            self.skipTest('symlink creation unavailable')
        self.assertFalse(hook.bounded_path(self.project, 'escape/config'))
        (self.project / '.agentic').symlink_to(self.project / 'other', target_is_directory=True)
        with self.assertRaises(ValueError):
            hook.private_dir(self.project)

    def test_codex_updated_input_preserves_original_assignment(self):
        payload = {'hook_event_name': 'PreToolUse', 'session_id': 'root', 'tool_use_id': 'spawn',
                   'tool_name': 'spawn_agent', 'tool_input': {'agent_type': 'developer', 'message': 'Build API', 'fork_context': True}}
        with patch.object(hook, 'codex_models', return_value=[{'id': 'cheap'}, {'id': 'costly'}]), patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'cheap')):
            result = hook.codex_event(self.project, payload)['hookSpecificOutput']
        self.assertEqual(result['permissionDecision'], 'allow')
        self.assertEqual(result['updatedInput'], {**payload['tool_input'], 'model': 'cheap'})

    def test_real_contract_key_separation_and_eight_second_timeout(self):
        request = {'state': {}, 'questions': {'permission': hook.choice('Is operation allowed?', {'allow': 'bounded', 'ask': 'user'})}}
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({'model': 'jev-1.13.0', 'answers': self.answer(request, 'ask')['answers']}).encode()
        opener = MagicMock()
        opener.open.return_value = response
        for endpoint, key_name in [('https://api.typesafe.ai/v1/systemone', 'TYPESAFE_API_KEY'), ('https://jevtypesafeai.com/api/v1/decide', 'JEV_API_KEY')]:
            with patch.dict(os.environ, {key_name: 'synthetic-secret'}, clear=True), patch.object(hook.urllib.request, 'build_opener', return_value=opener):
                self.assertEqual(hook.evaluate(self.project, {'api_url': endpoint}, request)['status'], 'evaluated')
                self.assertEqual(opener.open.call_args.kwargs['timeout'], 8)
                self.assertEqual(opener.open.call_args.args[0].full_url, endpoint)

    def test_reviewer_uses_measured_prices_or_explicit_lightweight_fallback(self):
        models = [{'id': 'small', 'prices': [{'input': 1, 'output': 2}]}, {'id': 'large', 'prices': [{'input': 10, 'output': 20}]}]
        self.assertEqual(hook.review_model(models, {}), ('small', 'cheapest_eligible_catalog_price'))
        models[1]['prices'] = None
        self.assertEqual(hook.review_model(models, {'lightweight_model': 'small'}), ('small', 'configured_lightweight_price_unknown'))
        self.assertIsNone(hook.review_model(models, {}))

    def test_budget_reservation_and_unknown_charge_are_conservative(self):
        ledger = self.project / 'budget.json'
        ledger.write_text(json.dumps({'limit_usd': .02, 'committed_usd': 0, 'pending': {}}))
        with patch.dict(os.environ, {'AGENTIC_JEV_BUDGET_FILE': str(ledger)}):
            reservation = hook.reserve_budget()
            with self.assertRaises(ValueError):
                hook.reserve_budget()
            hook.settle_budget(reservation, .0002)
            self.assertAlmostEqual(json.loads(ledger.read_text())['committed_usd'], .0002)
            ledger.write_text(json.dumps({'limit_usd': 5, 'committed_usd': 0, 'pending': {}}))
            reservation = hook.reserve_budget()
            hook.settle_budget(reservation, None)
            self.assertEqual(json.loads(ledger.read_text())['committed_usd'], .02)

    def test_multiple_subagents_keep_distinct_native_observations(self):
        for agent in ('developer', 'qa'):
            result = hook.run_event(self.project, self.event('observation', agent=agent, observed_model='small'))
            self.assertEqual(result['agent'], agent)
        self.assertEqual(len(list((self.project / '.agentic/jev').glob('event-*.json'))), 2)

    def test_known_quota_failures_are_excluded_but_unknown_is_not_claimed_available(self):
        hook.run_event(self.project, self.event('availability', model='local/empty', cooldown_seconds=900, reason_code='provider_http_402'))
        models = [{'id': 'local/empty'}, {'id': 'local/one'}, {'id': 'local/two'}]
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'local/one')) as api:
            result = hook.run_event(self.project, self.event('spawn', event_id='next', models=models, agent='developer'))
            self.assertEqual(result['model'], 'local/one')
            catalog = api.call_args.args[2]['state']['models']
            self.assertNotIn('local/empty', [m['id'] for m in catalog])
            self.assertTrue(all(m['quota_status'] == 'unknown' for m in catalog))
