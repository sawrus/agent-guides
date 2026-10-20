"""Synthetic regressions for cwd and task-scoped permission evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import hook


class Boundaries(unittest.TestCase):
    def setUp(self):
        self.fixture = tempfile.TemporaryDirectory()
        self.base = Path(self.fixture.name)
        self.project = self.base / 'project'
        self.cwd = self.project / 'subdir'
        self.cwd.mkdir(parents=True)
        self.allowed_temp = self.base / 'allowed-temp'
        self.allowed_temp.mkdir()
        self.temp_patch = patch.object(hook.tempfile, 'gettempdir', return_value=str(self.allowed_temp))
        self.temp_patch.start()
        (self.project / '.agentic.json').write_text('{"settings":{"jev":{"enabled":true}}}')

    def tearDown(self):
        self.temp_patch.stop()
        self.fixture.cleanup()

    def eligible(self, command, **data):
        return hook.permission_boundaries(self.project, {'host': 'claude', 'kind': 'permission',
            'action': 'Bash', 'input': {'command': command, **data}})

    def test_relative_paths_use_command_cwd(self):
        (self.cwd / 'data.txt').write_text('synthetic')
        (self.project / 'data.txt').symlink_to(self.base / 'outside')
        self.assertTrue(self.eligible('cat data.txt', cwd=str(self.cwd)))

    def test_cwd_symlink_escape(self):
        (self.base / 'outside').write_text('synthetic')
        (self.cwd / 'data.txt').symlink_to(self.base / 'outside')
        self.assertFalse(self.eligible('cat data.txt', cwd=str(self.cwd)))

    def test_parent_and_absolute_paths(self):
        (self.project / 'data.txt').write_text('synthetic')
        self.assertTrue(self.eligible('cat ../data.txt', cwd=str(self.cwd)))
        self.assertFalse(self.eligible('cat ../../outside', cwd=str(self.cwd)))
        self.assertTrue(self.eligible('cat ' + str(self.project / 'data.txt'), cwd=str(self.cwd)))
        self.assertFalse(self.eligible('cat ' + str(self.base / 'outside'), cwd=str(self.cwd)))

    def test_unknown_and_relative_cwd_are_native(self):
        for cwd in (None, '', 'subdir', str(self.base / 'missing')):
            with self.subTest(cwd=cwd):
                self.assertFalse(self.eligible('cat data.txt', **({'cwd': cwd} if cwd is not None else {})))
        self.assertFalse(self.eligible('pwd'))

    def test_secret_target_is_native(self):
        (self.cwd / 'data.txt').symlink_to(self.project / '.env')
        self.assertFalse(self.eligible('cat data.txt', cwd=str(self.cwd)))

    def test_on_rotates_task_even_for_same_prompt_and_event_id(self):
        def event(kind, **extra):
            return {'host': 'opencode', 'kind': kind, 'session_id': 'root', 'event_id': 'same', **extra}
        prompt = event('prompt', prompt='hello')
        context_path = self.project / '.agentic/jev' / ('context-' + hook.short_hash('root') + '.json')
        hook.run_event(self.project, prompt)
        first = json.loads(context_path.read_text())
        hook.run_event(self.project, event('prompt', prompt='jev on'))
        hook.run_event(self.project, prompt)
        second = json.loads(context_path.read_text())
        self.assertNotEqual(first['task_id'], second['task_id'])

    def test_explicit_new_workflow_clears_permission_history(self):
        workflows = self.project / '.agent/workflows'
        workflows.mkdir(parents=True)
        for name in ('build', 'debug'):
            (workflows / (name + '.md')).write_text(f'---\nname: {name}\ntype: workflow\ntrigger: /{name}\ndescription: test\nroles:\n  - developer\nselection:\n  use-when: test\n---\n')
        def prompt(text, identity):
            return hook.run_event(self.project, {'host': 'opencode', 'kind': 'prompt', 'session_id': 'root', 'event_id': identity, 'prompt': text})
        prompt('/build', '1')
        path = self.project / '.agentic/jev' / ('context-' + hook.short_hash('root') + '.json')
        context = json.loads(path.read_text())
        context['approved_decisions'] = [{'decision': 'allow', 'action': 'write'}]
        path.write_text(json.dumps(context))
        prompt('/debug', '2')
        self.assertNotIn('approved_decisions', json.loads(path.read_text()))

    def test_late_workflow_answer_cannot_undo_on(self):
        workflows = self.project / '.agent/workflows'
        workflows.mkdir(parents=True)
        (workflows / 'build.md').write_text('---\nname: build\ntype: workflow\ntrigger: /build\ndescription: implement\nroles:\n  - developer\nselection:\n  use-when: implementation\n---\n')
        def evaluate(project, settings, request):
            hook.run_event(self.project, {'host': 'opencode', 'kind': 'prompt', 'session_id': 'root', 'event_id': 'reset', 'prompt': 'jev on'})
            return {'status': 'evaluated', 'answers': {'workflow': {'choice': 'build', 'confidence': 1}}}
        with patch.object(hook, 'evaluate', side_effect=evaluate):
            result = hook.run_event(self.project, {'host': 'opencode', 'kind': 'prompt', 'session_id': 'root', 'event_id': 'old', 'prompt': 'Implement feature'})
        path = self.project / '.agentic/jev' / ('context-' + hook.short_hash('root') + '.json')
        self.assertNotIn('task_id', json.loads(path.read_text()))
        self.assertNotIn('workflow', result)

    def test_late_permission_answer_cannot_undo_on(self):
        hook.run_event(self.project, {'host': 'opencode', 'kind': 'prompt', 'session_id': 'root', 'prompt': 'jev on'})
        def evaluate(project, settings, request):
            hook.run_event(self.project, {'host': 'opencode', 'kind': 'prompt', 'session_id': 'root', 'prompt': 'jev on'})
            return {'status': 'evaluated', 'answers': {'permission': {'choice': 'allow', 'confidence': 1}}}
        with patch.object(hook, 'evaluate', side_effect=evaluate):
            result = hook.run_event(self.project, {'host': 'opencode', 'kind': 'permission', 'session_id': 'root', 'action': 'write', 'resources': ['new.txt']})
        path = self.project / '.agentic/jev' / ('context-' + hook.short_hash('root') + '.json')
        self.assertNotIn('approved_decisions', json.loads(path.read_text()))
        self.assertIsNone(result.get('decision'))

    def test_cached_allow_rechecks_symlink_boundary(self):
        path = self.cwd / 'data.txt'
        path.write_text('synthetic')
        event = {'host': 'claude', 'kind': 'permission', 'session_id': 'root', 'event_id': 'same',
                 'action': 'Bash', 'input': {'command': 'cat data.txt', 'cwd': str(self.cwd)}}
        with patch.object(hook, 'evaluate', return_value={'status': 'evaluated', 'answers': {'permission': {'choice': 'allow', 'confidence': 1}}}) as api:
            self.assertEqual(hook.run_event(self.project, event)['decision'], 'allow')
            path.unlink()
            path.symlink_to(self.base / 'outside')
            self.assertNotEqual(hook.run_event(self.project, event).get('decision'), 'allow')
        self.assertEqual(api.call_count, 1)
