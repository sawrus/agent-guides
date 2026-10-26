"""Offline tests of the shared quality gate (extensions/codex/hooks/gate/gate.py)."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import gate

AUTHOR = ['-c', 'user.name=t', '-c', 'user.email=t@localhost']


def project(makefile, changelog=True):
    root = Path(tempfile.mkdtemp(prefix='gate-'))
    (root / 'Makefile').write_text(makefile)
    (root / 'app.py').write_text('x = 1\n')
    if changelog:
        (root / 'CHANGELOG.md').write_text('# Changelog\n\n## Unreleased\n')
    subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
    subprocess.run(['git', 'add', '-A'], cwd=root, check=True)
    subprocess.run(['git', *AUTHOR, 'commit', '-q', '-m', 'init'], cwd=root, check=True)
    return root


GREEN = 'test:\n\t@true\nlint:\n\t@true\n'
RED = 'test:\n\t@echo boom; exit 1\nlint:\n\t@true\n'


class StopGate(unittest.TestCase):
    def test_unchanged_tree_runs_nothing(self):
        root = project(RED)
        self.assertEqual(gate.stop(root, {'session_id': 's'}), {})
        self.assertEqual(json.loads((root / '.agentic/gate/last.json').read_text())['checks'], [])

    def test_install_baseline_is_not_a_change(self):
        root = project(RED)
        (root / 'AGENTS.md').write_text('guide\n')
        (root / '.agentic/gate').mkdir(parents=True)
        digest = hashlib.sha256(b'guide\n').hexdigest()
        (root / '.agentic/gate/baseline.json').write_text(json.dumps({'files': {'AGENTS.md': digest}}))
        self.assertEqual(gate.stop(root, {'session_id': 's'}), {})
        (root / 'AGENTS.md').write_text('edited\n')
        self.assertEqual(gate.stop(root, {'session_id': 's'})['decision'], 'block')

    def test_failed_check_blocks_with_output(self):
        root = project(RED)
        (root / 'app.py').write_text('x = 2\n')
        result = gate.stop(root, {'session_id': 's'})
        self.assertEqual(result['decision'], 'block')
        self.assertIn('make test', result['reason'])
        self.assertIn('boom', result['reason'])

    def test_changelog_is_asked_once(self):
        root = project(GREEN)
        (root / 'app.py').write_text('x = 2\n')
        self.assertIn('CHANGELOG', gate.stop(root, {'session_id': 's'})['reason'])
        self.assertEqual(gate.stop(root, {'session_id': 's'}), {})

    def test_changelog_entry_passes(self):
        root = project(GREEN)
        (root / 'app.py').write_text('x = 2\n')
        (root / 'CHANGELOG.md').write_text('# Changelog\n\n## Unreleased\n\n- Fix x.\n')
        self.assertEqual(gate.stop(root, {'session_id': 's'}), {})
        self.assertTrue(json.loads((root / '.agentic/gate/last.json').read_text())['passed'])

    def test_tests_only_change_needs_no_changelog(self):
        root = project(GREEN)
        (root / 'tests').mkdir()
        (root / 'tests/test_x.py').write_text('')
        self.assertEqual(gate.stop(root, {'session_id': 's'}), {})

    def test_blocks_are_bounded(self):
        root = project(RED, changelog=False)
        (root / 'app.py').write_text('x = 2\n')
        outcomes = [gate.stop(root, {'session_id': 's'}) for _ in range(4)]
        self.assertEqual([bool(o) for o in outcomes], [True, True, True, False])

    def test_settings_override_commands(self):
        root = project(RED, changelog=False)
        (root / '.agent').mkdir()
        (root / '.agent/gate.json').write_text('{"commands": ["true"]}')
        (root / 'app.py').write_text('x = 2\n')
        self.assertEqual(gate.stop(root, {'session_id': 's'}), {})


class Guard(unittest.TestCase):
    def deny(self, payload):
        return gate.guard(Path(tempfile.mkdtemp()), payload).get('hookSpecificOutput', {}).get('permissionDecision')

    def test_secret_reads_are_denied(self):
        self.assertEqual(self.deny({'tool_name': 'Read', 'tool_input': {'file_path': '/p/.env'}}), 'deny')
        self.assertEqual(self.deny({'tool_name': 'Bash', 'tool_input': {'command': 'cat config/.env.prod'}}), 'deny')
        self.assertIsNone(self.deny({'tool_name': 'Read', 'tool_input': {'file_path': '/p/.env.example'}}))

    def test_force_push_is_denied(self):
        self.assertEqual(self.deny({'tool_name': 'Bash', 'tool_input': {'command': 'git push -f origin main'}}), 'deny')
        self.assertIsNone(self.deny({'tool_name': 'Bash', 'tool_input': {'command': 'git push --force-with-lease'}}))

    def test_recursive_delete_outside_project_is_denied(self):
        self.assertEqual(self.deny({'tool_name': 'Bash', 'tool_input': {'command': 'rm -rf ~/work'}}), 'deny')
        self.assertIsNone(self.deny({'tool_name': 'Bash', 'tool_input': {'command': 'rm -rf build'}}))

    def test_ordinary_commands_pass(self):
        self.assertIsNone(self.deny({'tool_name': 'Bash', 'tool_input': {'command': 'make test'}}))


if __name__ == '__main__':
    unittest.main()
