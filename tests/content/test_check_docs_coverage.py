"""scripts/check_docs_coverage.py on a throwaway git repository (DOC-3, DOC-4, DOC-5, DOC-6)."""

import contextlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import check_docs_coverage as cdc

ENV = {**os.environ, 'GIT_AUTHOR_NAME': 't', 'GIT_AUTHOR_EMAIL': 't@example.com', 'GIT_COMMITTER_NAME': 't',
       'GIT_COMMITTER_EMAIL': 't@example.com', 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_CONFIG_NOSYSTEM': '1'}
PAGE = '---\ncovers:\n  - src/**\n---\n\n# Tool\n\nBehaviour v{n}.\n'


class DocsCoverageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.git('init', '-q', '-b', 'main')
        self.write('docs/tool.md', PAGE.format(n=1))
        self.write('src/app.py', 'print(1)\n')
        self.write('other/tool.sh', 'echo 1\n')
        self.write('tests/test_app.py', 'pass\n')
        self.commit('base')
        self.git('checkout', '-q', '-b', 'feature')

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True, text=True,
                              env=ENV).stdout

    def write(self, rel, text):
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def commit(self, message):
        self.git('add', '-A')
        self.git('commit', '-q', '-m', message)

    def check(self, *extra):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cdc.main(['--repo', str(self.repo), '--base', 'main', '--config', str(self.repo / 'none.toml'),
                             *extra])
        return code, out.getvalue()

    def test_covered_change_passes(self):
        self.write('src/app.py', 'print(2)\n')
        self.write('docs/tool.md', PAGE.format(n=2))
        self.commit('feat: change app and docs')
        self.assertEqual(self.check()[0], 0)

    def test_uncovered_change_fails(self):
        self.write('src/app.py', 'print(2)\n')
        self.commit('feat: change app only')
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn('DOC-4  src/app.py', out)
        self.assertIn('update docs/tool.md', out)

    def test_deleted_file_is_covered_by_the_page_that_dropped_its_glob(self):
        self.write('docs/tool.md', '---\ncovers:\n  - src/**\n  - other/tool.sh\n---\n\n# Tool\n')
        self.commit('docs: cover the helper')
        self.git('branch', '-f', 'main')
        (self.repo / 'other/tool.sh').unlink()
        self.write('docs/tool.md', PAGE.format(n=2))
        self.commit('chore: remove the helper')
        self.assertEqual(self.check()[0], 0)

    def test_tests_and_ci_are_not_code(self):
        self.write('tests/test_app.py', 'assert True\n')
        self.write('.github/workflows/ci.yml', 'on: push\n')
        self.commit('test: more tests')
        self.assertEqual(self.check()[0], 0)

    def test_trailer_exempts_only_its_commits(self):
        self.write('src/app.py', 'print(2)\n')
        self.commit('refactor: rename\n\nDocs-Not-Needed: refactoring without behaviour change')
        self.assertEqual(self.check()[0], 0)
        self.write('other/tool.sh', 'echo 2\n')
        self.commit('feat: change tool')
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn('DOC-4  other/tool.sh', out)
        self.assertIn('no docs page covers it', out)
        self.assertNotIn('src/app.py', out)

    def test_changed_page_without_covers_fails(self):
        self.write('docs/new-tool.md', '# New tool\n')
        self.commit('docs: add page')
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn('DOC-3  docs/new-tool.md', out)

    def test_catch_all_glob_fails(self):
        self.write('docs/tool.md', '---\ncovers:\n  - "**"\n---\n\n# Tool\n')
        self.write('other/tool.sh', 'echo 2\n')
        self.commit('docs: cover everything')
        code, out = self.check()
        self.assertEqual(code, 1)
        self.assertIn('DOC-6  docs/tool.md', out)
        self.assertIn('DOC-4  other/tool.sh', out)

    def test_report_uncovered(self):
        code, out = self.check('--report-uncovered')
        self.assertEqual(code, 0)
        self.assertIn('DOC-6  other/tool.sh', out)
        self.assertNotIn('src/app.py', out)
        self.assertNotIn('tests/test_app.py', out)
        self.assertEqual(self.check('--report-uncovered', '--fail-uncovered')[0], 1)

    def test_glob_semantics(self):
        self.assertTrue(cdc.matches('src/a/b.rs', ['src/**']))
        self.assertTrue(cdc.matches('src/b.rs', ['src/*.rs']))
        self.assertFalse(cdc.matches('src/a/b.rs', ['src/*.rs']))
        self.assertTrue(cdc.matches('a/tests/x.py', ['**/tests/**']))
        self.assertTrue(cdc.matches('tools/x/y', ['tools/x/']))
        self.assertEqual(cdc.parse_covers('---\ncovers: [a/**, "b.md"]\n---\n'), ['a/**', 'b.md'])
        self.assertEqual(cdc.parse_covers('---\ncovers: []\n---\n'), [])
        self.assertIsNone(cdc.parse_covers('# no front matter\n'))


if __name__ == '__main__':
    unittest.main()
