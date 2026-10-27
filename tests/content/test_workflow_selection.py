"""Workflow `selection` blocks: repository content, lint rules and the JEV request size of the real catalog."""

import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest

import lint_prompts

ROOT = Path(__file__).resolve().parents[2]
REQUEST_LIMIT = 32768
GENERAL = "areas/software/general/workflows/develop-feature.md"
VALID = 'type: workflow\nagent: qa\nselection:\n  general: false\n  use-when: "The request asks for a check."\n'


def write_workflow(areas: Path, rel: str, front: str) -> None:
    path = areas / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nname: {path.stem}\n{front}---\n\n## Steps\n", encoding="utf-8")


class RepositoryWorkflows(unittest.TestCase):
    def test_repository_workflows_have_no_issues(self):
        self.assertEqual(lint_prompts.check_workflows(ROOT / "areas"), [])

    def test_only_the_catch_all_workflow_is_general(self):
        questions = lint_prompts.load_questions()
        general = [p.relative_to(ROOT).as_posix() for p in sorted((ROOT / "areas").glob("**/workflows/*.md"))
                   if questions.parse_front(p.read_text(encoding="utf-8"))["selection"]["general"] is True]
        self.assertEqual(general, [GENERAL])

    def test_selection_text_never_names_the_held_out_case(self):
        for path in sorted((ROOT / "areas").glob("**/workflows/*.md")):
            selection = lint_prompts.load_questions().parse_front(path.read_text(encoding="utf-8"))["selection"]
            text = " ".join(str(v) for v in selection.values())
            self.assertIsNone(re.search(r"calculator|crud", text, re.I), path)

    def test_full_catalog_fits_the_jev_request_limit(self):
        questions = lint_prompts.load_questions()
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            target = project / ".agent/workflows"
            target.mkdir(parents=True)
            for path in (ROOT / "areas").glob("**/workflows/*.md"):
                shutil.copy(path, target / path.name)
            catalog = questions.workflow_catalog(project)
            request = questions.workflow_request("разработай небольшое приложение " * 120, catalog, project, {})
        self.assertGreaterEqual(len(catalog), 10)
        self.assertLess(len(json.dumps(request, ensure_ascii=False).encode()), REQUEST_LIMIT)


class SelectionLint(unittest.TestCase):
    def issues(self, files: dict[str, str]) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            areas = Path(tmp) / "areas"
            for rel, front in files.items():
                write_workflow(areas, rel, front)
            return lint_prompts.check_workflows(areas)

    def test_valid_block_passes(self):
        self.assertEqual(self.issues({"software/x/workflows/check.md": VALID}), [])

    def test_missing_or_invalid_blocks_fail(self):
        cases = {
            "type: workflow\nagent: qa\n": "missing `selection`",
            VALID.replace("general: false", "general: maybe"): "`selection.general` must be true or false",
            VALID.replace('"The request asks for a check."', '""'): "`selection.use-when` must be a non-empty",
            VALID.replace("The request asks for a check.", "x" * 301): "exceeds 300 chars",
            VALID + '  avoid-when: "{{OPTIONAL}}"\n': "`selection.avoid-when` must be a non-empty",
            VALID + "  priority: high\n": "unknown `selection` key `priority`",
            VALID.replace("type: workflow", "type: prompt"): "missing `type: workflow`",
        }
        for front, expected in cases.items():
            issues = self.issues({"software/x/workflows/check.md": front})
            self.assertEqual(len(issues), 1, issues)
            self.assertIn(expected, issues[0])

    def test_one_general_workflow_per_top_level_area(self):
        general = VALID.replace("general: false", "general: true")
        self.assertEqual(self.issues({"software/a/workflows/one.md": general, "devops/b/workflows/two.md": general}), [])
        issues = self.issues({"software/a/workflows/one.md": general, "software/b/workflows/two.md": general})
        self.assertEqual(len(issues), 1)
        self.assertIn("more than one `selection.general: true`", issues[0])


if __name__ == "__main__":
    unittest.main()
