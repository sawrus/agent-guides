import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lint_review_pipeline import WORKFLOWS, profile_body, validate, workflow_issues

# The pack workflows carry no Post-task review hook since the content cleanup (no roles, ART-W1). The hook
# contract stays for project or company workflows that opt in, so the checks run on this fixture.
ROLES = ['product-owner', 'developer', 'qa']
FIXTURE = """---
name: fixture
roles:
  - product-owner
  - developer
  - qa
execution:
  initiator: product-owner
---

### 1. Build — `@developer`

## Post-task review

- **Coordinator:** `@product-owner` (`execution.initiator`).
- **Actions:** load `REVIEW_PIPELINE.md`; hand the evidence to `instruction-reviewer` and `memory-curator`.
- **Once only:** review the top-level task once; nested workflows/increments hand observations to the parent.
  Do not launch inside fix/retest loops or after failed/deferred delivery.
- **Output:** `summary.md`.
- **Failure:** do not block successful delivery or retry automatically; apply changes in a separate requested task.
"""


class ReviewContractTests(unittest.TestCase):
    def test_repository_contracts(self):
        self.assertEqual(validate(), [])

    def test_pack_workflows_have_no_hook(self):
        self.assertEqual(WORKFLOWS, {})

    def test_fixture_passes(self):
        self.assertEqual(workflow_issues(FIXTURE, ROLES), [])

    def test_specialist_cannot_replace_sdlc_owner(self):
        changed = FIXTURE.replace('  - qa\n', '  - instruction-reviewer\n')
        self.assertIn('SDLC role matrix changed', workflow_issues(changed, ROLES))

    def test_wrong_coordinator_rejected(self):
        changed = FIXTURE.replace('**Coordinator:** `@product-owner`', '**Coordinator:** `@developer`')
        self.assertTrue(any('coordinator' in issue for issue in workflow_issues(changed, ROLES)))

    def test_nested_and_failed_delivery_exclusions_required(self):
        for token in ('nested workflows/increments', 'failed/deferred delivery', 'fix/retest loops'):
            with self.subTest(token=token):
                changed = FIXTURE.replace(token, 'removed')
                self.assertIn(f'hook missing contract: {token}', workflow_issues(changed, ROLES))

    def test_specialist_step_rejected(self):
        changed = FIXTURE + '\n### Review — `@memory-curator`\n'
        self.assertIn('specialists must not be SDLC steps', workflow_issues(changed, ROLES))

    def test_codex_write_capability_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'memory-curator.toml'
            path.write_text('sandbox_mode = "workspace-write"\ndeveloper_instructions = "example"\n')
            with self.assertRaisesRegex(ValueError, 'read-only'):
                profile_body(path)


if __name__ == '__main__':
    unittest.main()
