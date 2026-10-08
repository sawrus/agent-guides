import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lint_review_pipeline import ROOT, WORKFLOWS, profile_body, validate, workflow_issues


class ReviewContractTests(unittest.TestCase):
    def setUp(self):
        key = 'software/backend/develop-feature'
        self.roles = WORKFLOWS[key]
        self.text = (ROOT / 'areas/software/backend/workflows/develop-feature.md').read_text()

    def test_repository_contracts(self):
        self.assertEqual(validate(), [])

    def test_specialist_cannot_replace_sdlc_owner(self):
        changed = self.text.replace('  - designer\n', '  - instruction_reviewer\n')
        self.assertIn('SDLC role matrix changed', workflow_issues(changed, self.roles))

    def test_wrong_coordinator_rejected(self):
        changed = self.text.replace('**Coordinator:** `@product-owner`', '**Coordinator:** `@developer`')
        self.assertTrue(any('coordinator' in issue for issue in workflow_issues(changed, self.roles)))

    def test_nested_and_failed_delivery_exclusions_required(self):
        for token in ('nested workflows/increments', 'failed/deferred delivery', 'fix/retest loops'):
            with self.subTest(token=token):
                changed = self.text.replace(token, 'removed')
                self.assertIn(f'hook missing contract: {token}', workflow_issues(changed, self.roles))

    def test_specialist_step_rejected(self):
        changed = self.text + '\n### Review — `@memory_curator`\n'
        self.assertIn('specialists must not be SDLC steps', workflow_issues(changed, self.roles))

    def test_codex_write_capability_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'memory_curator.toml'
            path.write_text('sandbox_mode = "workspace-write"\ndeveloper_instructions = "example"\n')
            with self.assertRaisesRegex(ValueError, 'read-only'):
                profile_body(path)


if __name__ == '__main__':
    unittest.main()
