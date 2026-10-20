"""Native hook contracts: routing, failover, redaction, dedup and permission boundaries."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import api
import hook
import questions
import routing

PRICED = [{'id': 'local/light', 'description': 'cheap coder', 'prices': {'input': 1, 'output': 2}},
          {'id': 'local/frontier', 'description': 'hard research', 'prices': {'input': 10, 'output': 30}}]


def workflow_file(name, description, general=False):
    return (f'---\nname: {name}\ntype: workflow\ntrigger: /{name}\ndescription: {description}\n'
            f'inputs:\n  - task\noutputs:\n  - changes\nroles:\n  - developer\n  - qa\nexecution:\n  initiator: product-owner\n'
            f'agent: product-owner\nselection:\n  general: {str(general).lower()}\n  use-when: "{description}."\n---\n')


class Hooks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        (self.project / '.agentic.json').write_text(json.dumps({'settings': {'jev': {'enabled': True}}}))
        tiers_file = self.project / hook.OPENCODE_TIERS_FILE
        tiers_file.parent.mkdir(parents=True, exist_ok=True)
        tiers_file.write_text(json.dumps({'version': 1, 'providers': {'local': {
            'fast': 'local/light', 'frontier': 'local/frontier'}}}))
        workflows = self.project / '.agent/workflows'
        workflows.mkdir(parents=True, exist_ok=True)
        (workflows / 'develop-feature.md').write_text(workflow_file('develop-feature', 'Implement a small backend feature', True))
        (workflows / 'code-review.md').write_text(workflow_file('code-review', 'Review existing code'))
        (workflows / 'notes.md').write_text('---\nname: notes\ntype: prompt\ndescription: not a workflow\n---\n')
        roles = self.project / '.opencode/agents'
        roles.mkdir(parents=True, exist_ok=True)
        for role in ('developer', 'qa', 'instruction-reviewer'):
            (roles / (role + '.md')).write_text(f'---\ndescription: {role}\n---\n')
        codex_roles = self.project / '.codex/agents'
        codex_roles.mkdir(parents=True, exist_ok=True)
        for role in ('developer', 'qa', 'instruction-reviewer'):
            # Installed with JEV enabled: no `model =` line, so the profile is not a pin.
            (codex_roles / (role + '.toml')).write_text(f'description = "{role}"\n')

    def tearDown(self):
        self.environment.stop()
        self.temp.cleanup()

    def answer(self, request, selected, confidence=1):
        name, question = next(iter(request['questions'].items()))
        return {'status': 'evaluated', 'answers': {name: {'type': 'choice', 'choice': selected, 'confidence': confidence,
                'probabilities': {k: int(k == selected) for k in question['criteria']}}}, 'usage': {'input_tokens': 100}}

    def event(self, kind, **kwargs):
        return {'host': 'opencode', 'kind': kind, 'session_id': 'root', 'event_id': 'first', **kwargs}

    def test_off_does_not_read_keys_write_logs_or_call_network(self):
        (self.project / '.agentic.json').write_text('{"settings":{"jev":{"enabled":false}}}')
        with patch.object(api, 'key_for', side_effect=AssertionError('key read')), patch.object(hook, 'evaluate', side_effect=AssertionError('network')):
            self.assertEqual(hook.run_event(self.project, self.event('prompt'))['reason_code'], 'disabled')
        self.assertFalse((self.project / '.agentic/jev').exists())

    def test_codex_catalog_uses_only_profile_default_models_and_user_pins(self):
        home = self.project / 'codex-home'
        home.mkdir()
        (home / 'models_cache.json').write_text(json.dumps({'models': [
            {'slug': name, 'visibility': 'list'} for name in ('light', 'default', 'user-pin', 'unrelated-expensive')]}))
        runtime = self.project / '.agent/jev'
        runtime.mkdir(parents=True, exist_ok=True)
        (runtime / 'model-defaults.json').write_text('{"developer":"default","qa":"light"}')
        profiles = self.project / '.codex/agents'
        (profiles / 'custom.toml').write_text('model = "user-pin"\n')
        with patch.dict(os.environ, {'CODEX_HOME': str(home)}):
            self.assertEqual({m['id'] for m in hook.codex_models(self.project)}, {'light', 'default', 'user-pin'})
            (runtime / 'model-defaults.json').write_text(json.dumps({'version': 2, 'roles': {'developer': 'default'},
                                                                     'tiers': {'fast': 'light', 'frontier': 'unrelated-expensive'}}))
            self.assertEqual({m['id'] for m in hook.codex_models(self.project)}, {'light', 'default', 'user-pin', 'unrelated-expensive'})

    def test_codex_child_inherits_original_task_for_nested_routing(self):
        root = self.event('prompt', host='codex', prompt='/develop-feature build calculator')
        hook.run_event(self.project, root)
        hook.run_event(self.project, self.event('observation', host='codex', child_session_id='child', observed_model='light'))
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'fast')):
            event = self.event('spawn', session_id='child', models=PRICED)
            hook.run_event(self.project, event)
        self.assertEqual(event['session_id'], 'child')
        records = [json.loads(p.read_text()) for p in (self.project / '.agentic/jev').glob('event-*.json')]
        child = next(r for r in records if r['context']['kind'] == 'spawn')
        self.assertEqual(child['context']['original_prompt'], root['prompt'])

    def test_reviewer_ciphertext_is_unchanged_and_receives_only_current_task_packet(self):
        hook.run_event(self.project, self.event('prompt', prompt='/develop-feature calculator'))
        hook.run_event(self.project, self.event('prompt', session_id='other', event_id='other-task', prompt='/code-review unrelated'))
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'fast')):
            hook.run_event(self.project, self.event('spawn', event_id='developer', agent='developer', models=PRICED))
        ciphertext = 'gAAAA-opaque-assignment'
        payload = {'hook_event_name':'PreToolUse', 'session_id':'root', 'tool_use_id':'reviewer',
                   'tool_name':'spawn_agent', 'tool_input':{'agent_type':'instruction-reviewer', 'message':ciphertext}}
        with patch.object(hook, 'codex_models', return_value=[{'id':'gpt-6-luna'}, {'id':'heavy'}]):
            result = hook.codex_event(self.project, payload)['hookSpecificOutput']
        self.assertEqual(result['updatedInput']['message'], ciphertext)
        start = hook.codex_event(self.project, {'hook_event_name':'SubagentStart', 'session_id':'root',
                 'agent_id':'review-child', 'agent_type':'instruction-reviewer', 'model':'gpt-6-luna'})
        self.assertIn('.agentic/jev/review-', start['hookSpecificOutput']['additionalContext'])
        packet = json.loads(next((self.project / '.agentic/jev').glob('review-*.json')).read_text())
        self.assertTrue(any(d['questions'] for d in packet['decisions']))
        for decision in packet['decisions']:
            record = json.loads((self.project / decision['record']).read_text())
            self.assertEqual(record['context']['task_id'], packet['task_id'])

    def test_codex_encrypted_assignment_skips_jev_and_applies_role_default(self):
        (self.project / '.agent/jev').mkdir(parents=True, exist_ok=True)
        (self.project / '.agent/jev/model-defaults.json').write_text(json.dumps(
            {'version': 2, 'roles': {'developer': 'gpt-6.1-sol'}, 'tiers': {'fast': 'gpt-6-luna', 'balanced': 'gpt-6.1-sol'}}))
        def spawn(call_id, message):
            payload = {'hook_event_name': 'PreToolUse', 'session_id': 'root', 'tool_use_id': call_id, 'tool_name': 'spawn_agent',
                       'tool_input': {'agent_type': 'developer', 'message': message}}
            hook.codex_event(self.project, payload)
            records = [json.loads(p.read_text()) for p in (self.project / '.agentic/jev').glob('event-*.json')]
            return next(r for r in records if r['context'].get('event_id') == call_id)
        with patch.object(hook, 'codex_models', return_value=[{'id': 'gpt-6-luna'}, {'id': 'gpt-6.1-sol'}]):
            with patch.object(hook, 'evaluate', side_effect=AssertionError('paid call for an encrypted assignment')):
                record = spawn('encrypted', 'gAAAA-opaque-assignment')
            with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'fast')) as client:
                plain = spawn('plain', 'Implement the change')
        self.assertEqual((record['result']['reason_code'], record['result']['model'], record['model_source']),
                         ('assignment_unavailable', 'gpt-6.1-sol', 'role_default'))
        self.assertIsNone(record['request'])
        self.assertEqual((client.call_count, plain['result']['model']), (1, 'gpt-6-luna'))

    def test_opencode_review_packet_is_delivered_once_per_event_without_paid_review_call(self):
        hook.run_event(self.project, self.event('prompt', prompt='/develop-feature calculator'))
        event = self.event('spawn', event_id='reviewer', agent='instruction-reviewer', models=[{'id':'gpt-6-luna'}, {'id':'heavy'}])
        with patch.object(hook, 'evaluate', side_effect=AssertionError('paid review call')):
            result = hook.run_event(self.project, event)
            self.assertTrue((self.project / result['review_packet']).is_file())
            self.assertNotIn('review_packet', hook.run_event(self.project, event))
            handoff = hook.run_event(self.project, self.event('review_handoff', session_id='child', root_session_id='root', event_id='child-review', agent='instruction-reviewer'))
            self.assertEqual(handoff['review_packet'], result['review_packet'])

    def test_workflow_context_model_and_repeat_are_scoped(self):
        def respond(project, settings, request):
            return self.answer(request, 'develop-feature' if 'workflow' in request['questions'] else 'fast')
        with patch.object(hook, 'evaluate', side_effect=respond) as client:
            event = self.event('prompt', prompt='разработай калькулятор')
            result = hook.run_event(self.project, event)
            self.assertEqual(result['workflow']['id'], 'develop-feature')
            self.assertEqual(hook.run_event(self.project, event), result)
            self.assertEqual(client.call_count, 1)
            workflow_state = client.call_args.args[2]['state']
            self.assertEqual(set(workflow_state), {'original_request', 'original_request_truncated', 'installed_areas', 'repository'})
            criteria = client.call_args.args[2]['questions']['workflow']['criteria']
            self.assertEqual(set(criteria), {'develop-feature', 'code-review', 'native', 'clarify'})
            self.assertTrue(criteria['develop-feature'].startswith('GENERAL. '))
            self.assertEqual(result['workflow']['roles'], ['developer', 'qa'])
            self.assertEqual(result['workflow']['initiator'], 'product-owner')
            result = hook.run_event(self.project, self.event('spawn', event_id='spawn1', models=PRICED, agent='developer',
                                                             prompt='Implement 4 operations', role_default='local/frontier'))
            self.assertEqual((result['model'], result['tier'], result['model_source']), ('local/light', 'fast', 'jev_tier'))
            request = client.call_args.args[2]
            self.assertIn('least expensive sufficient model tier', request['questions']['model']['instructions'])
            self.assertEqual(set(request['questions']['model']['criteria']), {'fast', 'frontier', 'clarify'})
            state = request['state']
            self.assertEqual(state['original_request'], 'разработай калькулятор')
            self.assertEqual(state['workflow'], {'id': 'develop-feature', 'roles': ['developer', 'qa']})
            self.assertEqual(state['role_default'], {'model': 'local/frontier', 'tier': 'frontier'})
            self.assertEqual(state['candidates'], [{'tier': 'fast', 'model': 'local/light', 'relative_cost': 1.0},
                                                   {'tier': 'frontier', 'model': 'local/frontier', 'relative_cost': 13.33}])
            self.assertEqual((state['cost_source'], state['quota']), ('catalog_price', 'unknown'))
            self.assertNotIn('default_model', state)

    def test_explicit_workflow_and_models_are_preserved(self):
        with patch.object(hook, 'evaluate', side_effect=AssertionError('network')):
            result = hook.run_event(self.project, self.event('prompt', prompt='Follow /develop-feature'))
            self.assertEqual(result['status'], 'preserved')
            result = hook.run_event(self.project, self.event('spawn', models=[{'id': 'a'}, {'id': 'b'}], pinned_model='b', role_default='a'))
            self.assertEqual((result['status'], result['model_source']), ('preserved', 'pinned'))
            self.assertNotIn('model', result)
            result = hook.run_event(self.project, self.event('spawn', event_id='continued', models=[{'id': 'a'}, {'id': 'b'}], continuation=True))
            self.assertEqual(result['status'], 'preserved')

    def test_low_confidence_and_http_failure_fall_back(self):
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'develop-feature', .8)):
            self.assertEqual(hook.run_event(self.project, self.event('prompt', prompt='Build API'))['reason_code'], 'low_confidence')
        with patch.object(hook, 'evaluate', side_effect=TimeoutError()):
            self.assertEqual(hook.run_event(self.project, self.event('prompt', session_id='other', prompt='Build API'))['reason_code'], 'request_failed')

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
            # Ineligible requests never reach JEV (QR-D4): the host keeps its native decision.
            with patch.object(hook, 'evaluate', side_effect=AssertionError('paid call for ineligible request')):
                event['event_id'] = json.dumps(event)
                result = hook.run_event(self.project, event)
            self.assertEqual(result, {'status': 'fallback', 'reason_code': 'not_auto_allow_eligible'})
        self.assertTrue(hook.permission_boundaries(self.project, self.event('permission', action='bash', resources=['mkdir src'], input={'cwd': str(self.project)})))
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

    def write_defaults(self, data):
        (self.project / '.agent/jev').mkdir(parents=True, exist_ok=True)
        (self.project / '.agent/jev/model-defaults.json').write_text(json.dumps(data))

    def test_codex_updated_input_preserves_original_assignment(self):
        self.write_defaults({'version': 2, 'roles': {'developer': 'costly'}, 'tiers': {'fast': 'cheap', 'frontier': 'costly'}})
        payload = {'hook_event_name': 'PreToolUse', 'session_id': 'root', 'tool_use_id': 'spawn',
                   'tool_name': 'spawn_agent', 'tool_input': {'agent_type': 'developer', 'message': 'Build API', 'fork_context': True}}
        with patch.object(hook, 'codex_models', return_value=[{'id': 'cheap'}, {'id': 'costly'}]), patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'fast')):
            result = hook.codex_event(self.project, payload)['hookSpecificOutput']
        self.assertEqual(result['permissionDecision'], 'allow')
        self.assertEqual(result['updatedInput'], {**payload['tool_input'], 'model': 'cheap'})

    def test_real_contract_key_separation_and_eight_second_timeout(self):
        request = {'state': {'original_request': 'разработай'}, 'questions': {'permission': questions.choice('Is operation allowed?', {'allow': 'bounded', 'ask': 'user'})}}
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({'model': 'jev-1.13.0', 'answers': self.answer(request, 'ask')['answers']}).encode()
        opener = MagicMock()
        opener.open.return_value = response
        for endpoint, key_name in [('https://api.typesafe.ai/v1/systemone', 'TYPESAFE_API_KEY'), ('https://jevtypesafeai.com/api/v1/decide', 'JEV_API_KEY')]:
            with patch.dict(os.environ, {key_name: 'synthetic-secret'}, clear=True), patch.object(api.urllib.request, 'build_opener', return_value=opener):
                self.assertEqual(hook.evaluate(self.project, {'api_url': endpoint}, request)['status'], 'evaluated')
                self.assertEqual(opener.open.call_args.kwargs['timeout'], 8)
                self.assertEqual(opener.open.call_args.args[0].full_url, endpoint)
                self.assertIn('разработай'.encode(), opener.open.call_args.args[0].data)

    def test_reviewer_uses_measured_prices_or_explicit_lightweight_fallback(self):
        models = [{'id': 'small', 'prices': [{'input': 1, 'output': 2}]}, {'id': 'large', 'prices': [{'input': 10, 'output': 20}]}]
        self.assertEqual(routing.review_model(models, {}), ('small', 'cheapest_eligible_catalog_price'))
        models[1]['prices'] = None
        self.assertEqual(routing.review_model(models, {'lightweight_model': 'small'}), ('small', 'configured_lightweight_price_unknown'))
        self.assertIsNone(routing.review_model(models, {}))

    def test_follow_up_prompts_continue_the_task_without_a_call(self):
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'develop-feature')) as client:
            first = hook.run_event(self.project, self.event('prompt', prompt='Build API'))
            follow = hook.run_event(self.project, self.event('prompt', event_id='second', prompt='yes, go on'))
        self.assertEqual((first['workflow']['id'], client.call_count), ('develop-feature', 1))
        self.assertEqual(follow['reason_code'], 'session_follow_up')
        with patch.object(hook, 'evaluate', side_effect=AssertionError('explicit workflow needs no call')):
            explicit = hook.run_event(self.project, self.event('prompt', event_id='third', prompt='now run /code-review'))
            spawn = hook.run_event(self.project, self.event('spawn', event_id='s', agent='developer', models=[{'id': 'a'}]))
        self.assertEqual(explicit['workflow']['id'], 'code-review')
        self.assertEqual(spawn['model'], 'a')
        tasks = {r['context']['event_id']: r['context']['task_id'] for r in self.records()}
        self.assertEqual(tasks['second'], tasks['first'])
        self.assertEqual(tasks['third'], tasks['s'])
        self.assertNotEqual(tasks['first'], tasks['third'])

    def test_native_first_prompt_turns_the_session_off_but_keeps_role_defaults(self):
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'native')):
            self.assertEqual(hook.run_event(self.project, self.event('prompt', prompt='Explain'))['reason_code'], 'native_request')
        with patch.object(hook, 'evaluate', side_effect=AssertionError('session is off')):
            self.assertEqual(hook.run_event(self.project, self.event('prompt', event_id='2', prompt='Build API'))['reason_code'], 'session_off')
            spawn = hook.run_event(self.project, self.event('spawn', event_id='3', agent='developer', models=PRICED, role_default='local/light'))
            permission = hook.run_event(self.project, self.event('permission', event_id='4', action='edit', resources=['a.py']))
        self.assertEqual((spawn['reason_code'], spawn['model'], spawn['model_source']), ('session_off', 'local/light', 'role_default'))
        self.assertEqual(permission['reason_code'], 'session_off')
        with patch.object(hook, 'evaluate', side_effect=AssertionError('other sessions are independent')):
            other = hook.run_event(self.project, self.event('prompt', session_id='other', prompt='Follow /develop-feature'))
        self.assertEqual(other['status'], 'preserved')

    def test_clarify_and_low_confidence_gate_the_session(self):
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'clarify')):
            hook.run_event(self.project, self.event('prompt', prompt='Change it'))
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'develop-feature')) as client:
            result = hook.run_event(self.project, self.event('prompt', event_id='2', prompt='Add a login endpoint'))
        self.assertEqual((result['workflow']['id'], client.call_count), ('develop-feature', 1))
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'develop-feature', .5)):
            hook.run_event(self.project, self.event('prompt', session_id='low', prompt='Build API'))
        context = json.loads(next(p for p in (self.project / '.agentic/jev').glob('context-*.json')
                                  if json.loads(p.read_text()).get('off_reason')).read_text())
        self.assertEqual((context['jev'], context['off_reason']), ('off', 'low_confidence'))

    def test_manual_switch_needs_no_call_and_on_restarts_workflow_selection(self):
        with patch.object(hook, 'evaluate', side_effect=AssertionError('switch is local')):
            off = hook.run_event(self.project, self.event('prompt', prompt=' /jev OFF '))
            self.assertEqual((off['status'], off['jev']), ('switched', 'off'))
            self.assertIn('manual', off['message'])
            self.assertEqual(hook.run_event(self.project, self.event('prompt', event_id='2', prompt='Build API'))['reason_code'], 'session_off')
            status = hook.run_event(self.project, self.event('prompt', event_id='3', prompt='Agentic JEV switch: status\nmore text'))
            self.assertEqual(status['jev'], 'off')
            self.assertEqual(hook.run_event(self.project, self.event('prompt', event_id='4', prompt='jev on'))['jev'], 'on')
        self.assertIsNone(hook.session_switch('please turn jev off later'))
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'develop-feature')) as client:
            hook.run_event(self.project, self.event('prompt', event_id='5', prompt='Build API'))
        self.assertEqual(client.call_count, 1)

    def test_observation_has_no_requested_model_and_usage_has_no_price(self):
        result = hook.run_event(self.project, self.event('observation', agent='developer', observed_model='small'))
        self.assertNotIn('requested_model', result)
        self.assertEqual(api.USAGE_KEYS, ('input_tokens', 'output_tokens'))
        self.assertFalse(hasattr(api, 'reserve_budget'))

    def test_multiple_subagents_keep_distinct_native_observations(self):
        for agent in ('developer', 'qa'):
            result = hook.run_event(self.project, self.event('observation', agent=agent, observed_model='small'))
            self.assertEqual(result['agent'], agent)
        result = hook.run_event(self.project, self.event('observation', agent='general', observed_model='small'))
        self.assertIsNone(result['agent'])
        records = [json.loads(p.read_text()) for p in (self.project / '.agentic/jev').glob('event-*.json')]
        self.assertEqual(len(records), 3)
        self.assertIn('general', [r['context'].get('native_agent_type') for r in records])

    def test_known_quota_failures_are_excluded_but_unknown_is_not_claimed_available(self):
        hook.run_event(self.project, self.event('availability', model='local/empty', cooldown_seconds=900, reason_code='provider_http_402'))
        models = [{'id': 'local/empty', 'prices': {'input': 0.1, 'output': 0.1}}] + PRICED
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'fast')) as client:
            result = hook.run_event(self.project, self.event('spawn', event_id='next', models=models, agent='developer'))
            self.assertEqual(result['model'], 'local/light')
            state = client.call_args.args[2]['state']
            self.assertNotIn('local/empty', [c['model'] for c in state['candidates']])
            self.assertEqual(state['quota'], 'unknown')

    def records(self, kind=None):
        found = [json.loads(p.read_text()) for p in (self.project / '.agentic/jev').glob('event-*.json')]
        return [r for r in found if kind is None or r['context']['kind'] == kind]

    def test_native_and_clarify_answers_keep_native_behaviour_with_reason_codes(self):
        for index, (selected, reason) in enumerate((('native', 'native_request'), ('clarify', 'clarification_needed'))):
            with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, selected)):
                result = hook.run_event(self.project, self.event('prompt', session_id=f's{index}', event_id=f'p{index}', prompt='Explain the module'))
            self.assertEqual((result['status'], result['reason_code']), ('fallback', reason))
            self.assertNotIn('workflow', result)
        record = self.records('prompt')[0]
        self.assertEqual({k: record[k] for k in ('applied', 'outcome', 'threshold')}, {'applied': True, 'outcome': 'native', 'threshold': .9})
        self.assertIn(record['decision'], ('native', 'clarify'))

    def test_role_default_on_codex_and_opencode_fallbacks(self):
        self.write_defaults({'version': 2, 'roles': {'developer': 'gpt-6.1-sol'}, 'tiers': {'fast': 'gpt-6-luna', 'balanced': 'gpt-6.1-sol'}})
        payload = {'hook_event_name': 'PreToolUse', 'session_id': 'root', 'tool_use_id': 'codex-low', 'tool_name': 'spawn_agent',
                   'tool_input': {'agent_type': 'developer', 'message': 'Build API'}}
        codex = [{'id': 'gpt-6-luna'}, {'id': 'gpt-6.1-sol'}]
        with patch.object(hook, 'codex_models', return_value=codex), patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'fast', .5)):
            output = hook.codex_event(self.project, payload)['hookSpecificOutput']
        self.assertEqual(output['updatedInput']['model'], 'gpt-6.1-sol')
        self.assertTrue(output['additionalContext'].startswith('Role default gpt-6.1-sol'))
        with patch.object(hook, 'evaluate', side_effect=AssertionError('no tiers, no call')):
            result = hook.run_event(self.project, self.event('spawn', event_id='oc', agent='developer', role_default='b',
                                                             models=[{'id': 'a'}, {'id': 'b', 'prices': {'input': 1, 'output': 1}}]))
        self.assertEqual((result['reason_code'], result['model'], result['model_source']), ('no_tier_routing', 'b', 'role_default'))
        spawn = next(r for r in self.records('spawn') if r['context']['event_id'] == 'oc')
        self.assertEqual((spawn['outcome'], spawn['model_source'], spawn['applied']), ('role_default_applied', 'role_default', False))
        self.assertEqual(spawn['result']['status'], 'fallback')

    def test_clarify_and_api_error_route_to_role_default(self):
        cases = (('clarify', lambda p, s, r: self.answer(r, 'clarify'), 'clarification_needed'), ('error', TimeoutError(), 'request_failed'))
        for event_id, effect, reason in cases:
            with patch.object(hook, 'evaluate', side_effect=effect):
                result = hook.run_event(self.project, self.event('spawn', event_id=event_id, agent='developer', models=PRICED, role_default='local/light'))
            self.assertEqual((result['reason_code'], result['model'], result['tier']), (reason, 'local/light', 'fast'))

    def test_configured_thresholds_and_invalid_values(self):
        # Model answers default to 0.6: below it the role default applies, above it JEV's tier.
        for thresholds, expected in (({'model': .5}, 'local/frontier'), ({'model': .3}, None), ({'model': 'x'}, None)):
            settings = {'jev': {'enabled': True, 'thresholds': thresholds}}
            (self.project / '.agentic.json').write_text(json.dumps({'settings': settings}))
            with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'frontier', .55)):
                result = hook.run_event(self.project, self.event('spawn', event_id=json.dumps(thresholds), agent='x', models=PRICED))
            self.assertEqual(result.get('model'), expected)
        self.assertEqual(questions.threshold({'thresholds': {'workflow': 1}}, 'workflow'), 1.0)
        self.assertEqual(questions.threshold({'thresholds': {'workflow': True}}, 'workflow'), .9)
        self.assertEqual(sorted(r['threshold'] for r in self.records('spawn')), [.5, .6, .6])

    def test_legacy_flat_codex_defaults_still_give_role_default(self):
        self.write_defaults({'developer': 'gpt-6.1-sol'})
        payload = {'hook_event_name': 'PreToolUse', 'session_id': 'root', 'tool_use_id': 'legacy', 'tool_name': 'spawn_agent',
                   'tool_input': {'agent_type': 'developer', 'message': 'Build API'}}
        with patch.object(hook, 'codex_models', return_value=[{'id': 'gpt-6-luna'}, {'id': 'gpt-6.1-sol'}]), patch.object(hook, 'evaluate', side_effect=AssertionError('paid')):
            output = hook.codex_event(self.project, payload)['hookSpecificOutput']
        self.assertEqual(output['updatedInput']['model'], 'gpt-6.1-sol')

    def test_settings_tier_override_must_be_a_candidate(self):
        settings = {'jev': {'enabled': True, 'tiers': {'fast': 'local/frontier', 'frontier': 'unknown/model'}}}
        (self.project / '.agentic.json').write_text(json.dumps({'settings': settings}))
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'fast')):
            result = hook.run_event(self.project, self.event('spawn', event_id='override', agent='developer', models=PRICED))
        self.assertEqual(result['model'], 'local/frontier')

    def test_identity_is_versioned_and_partial_runtime_falls_back(self):
        event = self.event('observation', agent='developer', observed_model='small')
        hook.run_event(self.project, event)
        identity = {k: None for k in hook.IDENTITY_KEYS}
        identity.update({k: event.get(k) for k in hook.IDENTITY_KEYS if k in event}, v=2)
        digest = hook.hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        self.assertTrue((self.project / '.agentic/jev' / ('event-' + digest + '.json')).is_file())
        with patch.object(hook, 'questions', None), patch.object(hook, 'evaluate', side_effect=AssertionError('paid')):
            self.assertEqual(hook.run_event(self.project, self.event('prompt', event_id='x'))['reason_code'], 'runtime_incomplete')

    def test_permission_state_is_metadata_only_and_keeps_decision_history(self):
        (self.project / 'src.py').write_text('PRIVATE_BODY = 1\n')
        hook.run_event(self.project, self.event('prompt', prompt='/develop-feature add field'))
        seen = []
        def respond(project, settings, request):
            seen.append(request)
            return self.answer(request, 'allow')
        events = [self.event('permission', event_id='w', action='write', agent='developer', resources=[str(self.project / 'src.py')],
                             input={'content': 'PRIVATE_BODY = 2'}),
                  self.event('permission', event_id='b', action='bash', agent='build', input={'command': 'ls -la PRIVATE_FLAG', 'cwd': str(self.project)}),
                  self.event('permission', event_id='c', action='bash', agent='build', input={'command': 'pytest -q && echo PRIVATE_FLAG'})]
        with patch.object(hook, 'evaluate', side_effect=respond):
            decisions = [hook.run_event(self.project, e).get('decision') for e in events]
        self.assertEqual(decisions, ['allow', 'allow', None])
        self.assertEqual(len(seen), 2)
        text = json.dumps([r['state'] for r in seen])
        self.assertNotIn('PRIVATE_BODY', text)
        self.assertNotIn('PRIVATE_FLAG', text)
        first, second = seen[0]['state'], seen[1]['state']
        self.assertEqual(first['targets'], [{'path': 'src.py', 'in_project': True, 'new_file': False, 'bytes': 17, 'kind': 'source'}])
        self.assertEqual((first['agent'], first['workflow']['id']), ('developer', 'develop-feature'))
        self.assertEqual(second['command'], {'program': 'ls', 'length': 19, 'args': 2, 'shell_operators': []})
        self.assertEqual((second['agent'], second['native_agent_type']), (None, 'build'))
        self.assertEqual(second['approved_decisions'], [{'action': 'write', 'decision': 'allow', 'targets': ['src.py']}])
        skipped = next(r for r in self.records('permission') if r['context']['event_id'] == 'c')
        self.assertEqual({k: skipped[k] for k in ('request', 'decision', 'applied', 'outcome')},
                         {'request': None, 'decision': None, 'applied': False, 'outcome': 'native'})
        self.assertEqual(skipped['result']['reason_code'], 'not_auto_allow_eligible')

    def test_confident_allow_still_downgrades_when_eligibility_is_lost(self):
        turn = SimpleNamespace(event={'auto_allow_eligible': False}, context={}, context_path=None, project=self.project)
        plan = {'result': {'status': 'evaluated'}, 'fields': {}}
        hook.map_permission(turn, plan, 'allow')
        self.assertEqual((plan['result']['decision'], plan['fields']['outcome']), ('ask', 'ask_downgrade'))

    def test_partial_runtime_writes_identifier_only_records(self):
        payload = {'hook_event_name': 'UserPromptSubmit', 'session_id': 's', 'turn_id': 't', 'prompt': 'PRIVATE prompt text'}
        with patch.object(hook, 'adapters', None):
            self.assertEqual(hook.codex_event(self.project, payload), {})
            self.assertEqual(hook.claude_event(self.project, {**payload, 'session_id': 's2'}), {})
        with patch.object(hook, 'questions', None):
            self.assertEqual(hook.run_event(self.project, self.event('prompt', prompt='PRIVATE'))['reason_code'], 'runtime_incomplete')
        records = self.records()
        self.assertEqual(sorted(r['context']['host'] for r in records), ['claude', 'codex', 'opencode'])
        self.assertTrue(all(r['result']['reason_code'] == 'runtime_incomplete' and r['outcome'] == 'native' for r in records))
        self.assertNotIn('PRIVATE', json.dumps(records))
        (self.project / '.agentic.json').write_text('{"settings":{"jev":{"enabled":false}}}')
        with patch.object(hook, 'adapters', None):
            hook.codex_event(self.project, {**payload, 'session_id': 'off'})
        self.assertEqual(len(self.records()), 3)

    def test_request_is_kept_when_answer_mapping_fails(self):
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'develop-feature')), \
                patch.dict(hook.MAPPERS, {'workflow': MagicMock(side_effect=KeyError('broken'))}):
            result = hook.run_event(self.project, self.event('prompt', prompt='Build API'))
        self.assertEqual(result['reason_code'], 'request_failed')
        self.assertIn('workflow', self.records('prompt')[0]['request']['questions'])

    def test_requests_and_injected_context_never_name_the_test_case(self):
        self.write_defaults({'version': 2, 'roles': {}, 'tiers': {'fast': 'cheap', 'frontier': 'costly'}})
        sent = []
        def respond(project, settings, request):
            sent.append(request['questions'])
            return self.answer(request, 'develop-feature' if 'workflow' in request['questions'] else 'fast')
        prompt = {'hook_event_name': 'UserPromptSubmit', 'session_id': 's', 'turn_id': 't', 'prompt': 'Add a new endpoint'}
        spawn = {'hook_event_name': 'PreToolUse', 'session_id': 's', 'tool_use_id': 'u', 'tool_name': 'spawn_agent', 'tool_input': {'agent_type': 'developer', 'message': 'go'}}
        with patch.object(hook, 'evaluate', side_effect=respond), patch.object(hook, 'codex_models', return_value=[{'id': 'cheap'}, {'id': 'costly'}]):
            outputs = [hook.codex_event(self.project, prompt), hook.codex_event(self.project, spawn)]
        text = json.dumps([sent, outputs]).lower()
        self.assertEqual(len(sent), 2)
        self.assertNotIn('calculator', text)
        self.assertNotIn('crud', text)

    def test_missing_api_module_falls_back_with_runtime_incomplete(self):
        runtime = Path(hook.__file__).resolve().parent
        partial = self.project / 'partial-runtime'
        partial.mkdir()
        for name in ('hook.py', 'questions.py', 'routing.py', 'adapters.py'):
            shutil.copy(runtime / name, partial / name)
        # No PYTHONPATH: the script directory is the only import root, as in an installed .agent/jev/.
        environment = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'PYTHONDONTWRITEBYTECODE': '1'}
        event = json.dumps({'kind': 'prompt', 'session_id': 's', 'event_id': 'e', 'prompt': 'PRIVATE'})
        done = subprocess.run([sys.executable, str(partial / 'hook.py'), '--host', 'opencode', '--project-dir', str(self.project)],
                              input=event, capture_output=True, text=True, env=environment, timeout=30)
        self.assertEqual(json.loads(done.stdout), {'status': 'fallback', 'reason_code': 'runtime_incomplete'}, done.stderr)
        records = self.records()
        self.assertEqual([r['result']['reason_code'] for r in records], ['runtime_incomplete'])
        self.assertNotIn('PRIVATE', json.dumps(records))
