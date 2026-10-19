"""Question builders: frontmatter, workflow criteria, repository snapshot, tiers, permission metadata, thresholds."""
import json
import os
from pathlib import Path
import re
import tempfile
import unittest

import api
import questions
import routing

RUNTIME = Path(questions.__file__).resolve().parent
REQUEST_LIMIT = 32768
WORKFLOW = '''---
name: build-thing
type: workflow
trigger: /build-thing
description: "Build: a thing"
inputs:
  - task_description
outputs:
  - code
  - tests
roles:
  - developer
  - qa
execution:
  initiator: team-lead
agent: team-lead
selection:
  general: true
  use-when: "Any ordinary change to code: features, fixes and small programs."
  avoid-when: 'Pure questions'
---
body
'''


def synthetic(index):
    # Sizes follow the longest installed workflows; the prompt, not the catalog, is Cyrillic (AC-11).
    return {'id': f'specialized-workflow-{index:02d}', 'path': f'.agent/workflows/specialized-workflow-{index:02d}.md',
            'description': 'Design, implement and verify a specialized change with tests and documentation updates.',
            'trigger': '', 'initiator': 'developer', 'inputs': ['task_description', 'existing_codebase', 'constraints'],
            'outputs': ['implemented_changes', 'passing_tests', 'updated_docs'],
            'roles': ['product-owner', 'team-lead', 'developer', 'qa'], 'general': index == 0,
            'use_when': 'The request explicitly needs this specialized domain, its inputs and its outputs, for example a change '
                        'that only this area can deliver safely; ordinary requests use the general workflow instead.',
            'avoid_when': 'The request only asks a question.'}


class Frontmatter(unittest.TestCase):
    def test_parse_front_scalars_lists_and_maps(self):
        front = questions.parse_front(WORKFLOW)
        self.assertEqual(front['description'], 'Build: a thing')
        self.assertEqual(front['outputs'], ['code', 'tests'])
        self.assertEqual(front['execution'], {'initiator': 'team-lead'})
        self.assertEqual(front['selection']['general'], True)
        self.assertEqual(front['selection']['avoid-when'], 'Pure questions')
        self.assertIsNone(questions.front_block('no frontmatter'))
        self.assertEqual(questions.parse_front('---\nunterminated: yes\n'), {})

    def test_parse_workflow_requires_type_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            folder = project / '.agent/workflows'
            folder.mkdir(parents=True)
            (folder / 'build-thing.md').write_text(WORKFLOW)
            (folder / 'helper.md').write_text(WORKFLOW.replace('type: workflow', 'type: prompt'))
            catalog = questions.workflow_catalog(project)
        self.assertEqual([w['id'] for w in catalog], ['build-thing'])
        workflow = catalog[0]
        self.assertEqual((workflow['initiator'], workflow['general'], workflow['path']), ('team-lead', True, '.agent/workflows/build-thing.md'))
        criterion = questions.workflow_criterion(workflow, 0)
        for part in ('GENERAL. Build: a thing', 'task_description → Outputs: code, tests', 'Roles: developer, qa', 'Use when: Any ordinary', 'Avoid when: Pure'):
            self.assertIn(part, criterion)


class Criteria(unittest.TestCase):
    def test_eighty_workflows_with_cyrillic_prompt_fit_the_request_limit(self):
        catalog = [synthetic(index) for index in range(80)]
        with tempfile.TemporaryDirectory() as directory:
            request = questions.workflow_request('разработай небольшую программу ' * 200, catalog, Path(directory), {})
        api.validate(request)
        size = len(json.dumps(request, ensure_ascii=False).encode())
        self.assertLess(size, REQUEST_LIMIT)
        criteria = request['questions']['workflow']['criteria']
        self.assertEqual(len(criteria), 82)
        self.assertNotEqual(criteria['specialized-workflow-01'], questions.workflow_criterion(synthetic(1), 0))
        self.assertIn('native', criteria)
        self.assertIn('clarify', criteria)
        self.assertTrue(criteria['specialized-workflow-00'].startswith('GENERAL. '))
        self.assertTrue(request['state']['original_request_truncated'])
        self.assertEqual(len(request['state']['original_request']), questions.ORIGINAL_LIMIT)

    def test_small_catalog_keeps_full_criteria(self):
        full = questions.fit_criteria([synthetic(1)])
        self.assertEqual(full['specialized-workflow-01'], questions.workflow_criterion(synthetic(1), 0))


class Snapshot(unittest.TestCase):
    def test_snapshot_reports_bounded_facts_without_following_symlinks(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            project = Path(directory)
            for index in range(5):
                (Path(outside) / f'external{index}.py').write_text('')
            (project / '.git').mkdir()
            (project / 'Makefile').write_text('')
            (project / 'src').mkdir()
            (project / 'src/app.py').write_text('')
            (project / 'src/lib.rs').write_text('')
            (project / '.agent/jev').mkdir(parents=True)
            (project / '.agent/jev/hook.py').write_text('')
            os.symlink(outside, project / 'linked', target_is_directory=True)
            snapshot = questions.repo_snapshot(project)
            self.assertEqual(snapshot['source_files'], 2)
            self.assertEqual(sorted(snapshot['top_languages']), ['python', 'rust'])
            self.assertTrue(snapshot['is_git'] and snapshot['has_makefile'])
            self.assertFalse(snapshot['has_ci'] or snapshot['only_agent_guidance'] or snapshot['truncated'])
            self.assertTrue(questions.repo_snapshot(project, max_entries=2)['truncated'])
            # The deadline is checked per directory entry, before any entry is counted.
            expired = questions.repo_snapshot(project, seconds=-1)
            self.assertEqual((expired['truncated'], expired['is_git'], expired['source_files']), (True, False, 0))

    def test_depth_limit_and_guidance_only_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            deep = project.joinpath(*['d'] * 8)
            deep.mkdir(parents=True)
            (deep / 'x.py').write_text('')
            snapshot = questions.repo_snapshot(project, max_depth=3)
            self.assertEqual(snapshot['source_files'], 0)
            self.assertTrue(snapshot['truncated'])
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / 'AGENTS.md').write_text('')
            (project / '.claude').mkdir()
            self.assertTrue(questions.repo_snapshot(project)['only_agent_guidance'])

    def test_installed_areas_prefer_specializations(self):
        manifest = {'settings': {'areas': ['software'], 'specializations': ['software.general', 'software.backend']}}
        self.assertEqual(questions.installed_areas(manifest), ['software.backend', 'software.general'])
        self.assertEqual(questions.installed_areas({'settings': {'areas': ['devops']}}), ['devops'])
        self.assertEqual(questions.installed_areas(None), [])


class Tiers(unittest.TestCase):
    def test_v2_and_legacy_defaults(self):
        v2 = routing.load_defaults({'version': 2, 'roles': {'developer': 'sonnet'}, 'tiers': {'fast': 'haiku', 'huge': 'x'}})
        self.assertEqual(v2, {'roles': {'developer': 'sonnet'}, 'tiers': {'fast': 'haiku'}})
        self.assertEqual(routing.load_defaults({'developer': 'sonnet', 'n': 1}), {'roles': {'developer': 'sonnet'}, 'tiers': {}})
        self.assertEqual(routing.load_defaults([]), {'roles': {}, 'tiers': {}})

    def test_claude_and_codex_host_tiers(self):
        claude = routing.claude_models({'roles': {}, 'tiers': {}})
        self.assertEqual(routing.host_tiers('claude', claude, {}, None), routing.CLAUDE_TIERS)
        # A combined claude+codex install writes Codex tiers; Claude uses the built-in alias map (D7).
        self.assertEqual(routing.host_tiers('claude', claude, {'fast': 'gpt-6-luna'}, None), routing.CLAUDE_TIERS)
        codex = [{'id': 'gpt-6-luna'}, {'id': 'gpt-6.1-sol'}]
        configured = {'fast': 'gpt-6-luna', 'balanced': 'gpt-6.1-sol', 'frontier': 'gpt-6-astra'}
        self.assertEqual(routing.host_tiers('codex', codex, configured, None), {'fast': 'gpt-6-luna', 'balanced': 'gpt-6.1-sol'})
        pool = routing.candidates(codex, configured, 'tier_order')
        self.assertEqual(pool, [{'tier': 'fast', 'model': 'gpt-6-luna', 'relative_cost': 1}, {'tier': 'balanced', 'model': 'gpt-6.1-sol', 'relative_cost': 2}])

    def test_opencode_tiers_from_one_to_four_priced_models(self):
        def model(name, cost):
            return {'id': name, 'prices': cost}
        self.assertEqual(routing.opencode_tiers([model('a', {'input': 1, 'output': 1})]), {})
        two = [model('b', [{'input': 5, 'output': 5}]), model('a', {'input': 1, 'output': 1})]
        self.assertEqual(routing.opencode_tiers(two), {'fast': 'a', 'frontier': 'b'})
        three = two + [model('c', {'input': 2, 'output': 2})]
        self.assertEqual(routing.opencode_tiers(three), {'fast': 'a', 'balanced': 'c', 'frontier': 'b'})
        four = three + [model('d', {'input': 3, 'output': 3})]
        self.assertEqual(routing.opencode_tiers(four)['balanced'], 'c')
        self.assertEqual(routing.opencode_tiers(two + [model('u', None)]), {})
        self.assertEqual(routing.opencode_tiers([model('a', {'input': 1, 'output': 1}), model('b', {'input': 1, 'output': 1})]), {})
        pool = routing.candidates(three, routing.opencode_tiers(three), 'catalog_price')
        self.assertEqual([c['relative_cost'] for c in pool], [1.0, 2.0, 5.0])
        self.assertIsNone(routing.price({'input': True, 'output': 1}))


class Permission(unittest.TestCase):
    def test_targets_and_command_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory).resolve()
            (project / 'docs').mkdir()
            self.assertEqual(questions.permission_target(project, 'new.py'),
                             {'path': 'new.py', 'in_project': True, 'new_file': True, 'bytes': 0, 'kind': 'source'})
            self.assertEqual(questions.permission_target(project, 'docs')['kind'], 'directory')
            self.assertEqual(questions.permission_target(project, '.env'),
                             {'path': '.env', 'in_project': True, 'new_file': None, 'bytes': None, 'kind': 'secret_like'})
            self.assertEqual(questions.permission_target(project, 'tests/test_x.py')['kind'], 'test')
            self.assertEqual(questions.permission_target(project, '/etc/hosts'),
                             {'path': '[outside project]', 'in_project': False, 'new_file': None, 'bytes': None, 'kind': 'outside'})
            patch_event = {'action': 'apply_patch', 'input': {'patchText': '*** Add File: a.py\n+secret\n*** Delete File: b.md\n'}}
            request = questions.permission_request(patch_event, project, {}, False)
        self.assertEqual([t['path'] for t in request['state']['targets']], ['a.py', 'b.md'])
        self.assertNotIn('secret', json.dumps(request['state']))
        meta = questions.command_meta('cat a.txt | grep x > out; echo $(id)')
        self.assertEqual((meta['program'], meta['args']), ('cat', 8))
        self.assertEqual(meta['shell_operators'], ['$(', ';', '>', '|'])
        self.assertEqual(questions.command_meta(['ls', '-la'])['program'], 'ls')

    def test_outside_symlinks_and_secrets_are_never_inspected(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory(dir=Path.home()) as outside:
            project = Path(directory).resolve()
            (Path(outside) / 'private.txt').write_text('x' * 40)
            os.symlink(outside, project / 'link', target_is_directory=True)
            linked = questions.permission_target(project, 'link/private.txt')
            secret = questions.permission_target(project, str(Path(outside) / 'id.pem'))
            scratch = questions.permission_target(project, str(Path(tempfile.gettempdir()) / 'scratch.txt'))
        self.assertEqual((linked['path'], linked['bytes'], linked['kind']), ('[outside project]', None, 'outside'))
        self.assertEqual((secret['path'], secret['kind']), ('[outside project]', 'secret_like'))
        self.assertNotIn(outside, json.dumps([linked, secret]))
        self.assertEqual((scratch['path'], scratch['in_project'], scratch['new_file']), ('$TMPDIR/scratch.txt', False, True))

    def test_decision_history_is_capped(self):
        context = {}
        for index in range(15):
            questions.remember_decision(context, {'action': 'write', 'resources': [f'f{index}.py']}, 'allow', Path('/tmp/project'))
        self.assertEqual(len(context['approved_decisions']), questions.APPROVED_LIMIT)
        self.assertEqual(context['approved_decisions'][-1]['targets'], ['f14.py'])


class ModelRequest(unittest.TestCase):
    def test_assignment_is_truncated_and_session_model_is_absent(self):
        role = {'role': 'developer', 'assignment': 'x' * 3000, 'role_default': {'model': 'sonnet', 'tier': 'balanced'}}
        pool = [{'tier': 'fast', 'model': 'haiku', 'relative_cost': 1}, {'tier': 'frontier', 'model': 'opus', 'relative_cost': 3}]
        request = questions.model_request(role, pool, {'id': 'w', 'roles': ['developer'], 'path': 'p'}, 'original')
        api.validate(request)
        state = request['state']
        self.assertEqual((len(state['assignment']), state['assignment_truncated']), (questions.ASSIGNMENT_LIMIT, True))
        self.assertEqual(state['workflow'], {'id': 'w', 'roles': ['developer']})
        self.assertEqual(set(request['questions']['model']['criteria']), {'fast', 'frontier', 'clarify'})
        self.assertNotIn('default_model', state)

    def test_documented_example_matches_the_runtime_question(self):
        example = json.loads((RUNTIME.parents[3] / 'docs/jev-integration/example-request.json').read_text(encoding='utf-8'))
        state = example['state']
        rebuilt = questions.model_request({k: state[k] for k in ('role', 'role_description', 'role_default', 'assignment')},
                                          state['candidates'], state['workflow'], state['original_request'])
        self.assertEqual(example, rebuilt)


class Redaction(unittest.TestCase):
    def test_identifiers_with_key_prefixes_survive(self):
        for text in ('tests_and_review_evidence', 'rename the parts_inventory_service module', 'ts_inventory_service',
                     'task-ask-me', 'risk-sk-assessment', 'contexts_ok', 'sk-short', 'xoxb-1', 'AKIA1234'):
            self.assertEqual(api.redact(text), text)

    def test_provider_tokens_are_redacted(self):
        tokens = ('ts_live9aZk3QwErTy', 'sk-proj-Ab12Cd34Ef56', 'sk-proj-AbCdEfGhIjKlMnOp', 'sk-abcdefghijklmnopqrstuvwxyz',
                  'sk-ant-api03-AbCdEfGhIjKlMnOpQrSt', 'jv_live_8f3k2l1m0n9b', 'jv_live_abcdefghijklmnopqrst',
                  'ghp_' + 'a1B2' * 9, 'gho_' + 'Z' * 24, 'AKIAIOSFODNN7EXAMPLE', 'xoxb-1234567890-abcdefghij')
        for token in tokens:
            self.assertEqual(api.redact(f'key ({token}) end'), 'key ([REDACTED]) end', token)


class Thresholds(unittest.TestCase):
    def test_threshold_range_and_default(self):
        self.assertEqual(questions.threshold({'thresholds': {'model': .5}}, 'model'), .5)
        for invalid in (.49, 1.01, None, '0.7', False):
            self.assertEqual(questions.threshold({'thresholds': {'model': invalid}}, 'model'), questions.DEFAULT_THRESHOLD)
        self.assertEqual(questions.threshold(None, 'model'), .9)


class NoTestCaseInInstructions(unittest.TestCase):
    def test_runtime_sources_never_name_the_test_case(self):
        for name in ('hook.py', 'questions.py', 'routing.py', 'adapters.py'):
            text = (RUNTIME / name).read_text(encoding='utf-8')
            self.assertIsNone(re.search(r'calculator|crud', text, re.I), name)


if __name__ == '__main__':
    unittest.main()
