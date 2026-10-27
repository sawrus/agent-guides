"""Docs catalog: examples come from `Example request:` lines in workflows; prompt files are not read."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_docs_catalog as catalog

WORKFLOW = """---
name: fix-bug
type: workflow
trigger: /fix-bug
description: Fix a reproduced defect.
selection:
  general: false
  use-when: "A user reports a defect with steps to reproduce."
uses-skills: []
related-rules: []
---

# Fix a bug

Example request: `The login form accepts an empty password; fix it and add a test.`
**Example request:** Orders API returns 500 for an empty cart.

## 1. Reproduce

**Do**: run the failing case.
**Done when**: a test fails for the reported reason.
"""


class DocsCatalog(unittest.TestCase):
    def build(self, files):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for rel, text in files.items():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            with patch.object(catalog, "ROOT", root), patch.object(catalog, "AREAS_DIR", root / "areas"):
                return catalog.build_catalog(validate=True), catalog.build_catalog(validate=True, require_examples=True)

    def test_examples_and_use_when_come_from_the_workflow(self):
        (data, problems), _ = self.build({
            "areas/software/general/workflows/fix-bug.md": WORKFLOW,
            # A leftover prompt file is ignored.
            "areas/software/general/prompts/fix-bug.md": "---\nworkflow: fix-bug\n---\n# Prompt: /fix-bug\n",
        })
        self.assertEqual(problems, [])
        workflow = data["areas"][0]["workflows"][0]
        self.assertEqual(workflow["examples"], [
            "The login form accepts an empty password; fix it and add a test.",
            "Orders API returns 500 for an empty cart.",
        ])
        self.assertEqual(workflow["use_when"], "A user reports a defect with steps to reproduce.")
        self.assertEqual(workflow["roles"], [])
        self.assertNotIn("prompt_path", workflow)
        self.assertEqual(data["stats"], {"workflows": 1, "examples": 2, "problems": 0})

    def test_missing_example_is_a_problem_only_when_required(self):
        text = WORKFLOW.replace("Example request:", "Example:")
        (_, problems), (_, strict) = self.build({"areas/software/general/workflows/fix-bug.md": text})
        self.assertEqual(problems, [])
        self.assertEqual(len(strict), 1)
        self.assertIn("no `Example request:` line", strict[0])


if __name__ == "__main__":
    unittest.main()
