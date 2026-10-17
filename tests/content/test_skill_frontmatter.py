"""Verify every areas/**/skills/<dir>/SKILL.md is a valid Claude Code skill."""

from pathlib import Path
import tempfile
import unittest

import lint_prompts

ROOT = Path(__file__).resolve().parents[2]


def write_skill(areas: Path, rel: str, frontmatter: str) -> None:
    path = areas / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}\n---\n\n# Skill\n", encoding="utf-8")


class SkillFrontmatterTests(unittest.TestCase):
    def test_repository_skills_have_no_issues(self):
        self.assertEqual(lint_prompts.check_skills(ROOT / "areas"), [])

    def test_valid_sample_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            areas = Path(tmp) / "areas"
            write_skill(
                areas,
                "x/skills/good-skill/SKILL.md",
                'name: good-skill\ndescription: "Does a thing; use when needed."\n'
                "allowed-tools:\n  - Read\n  - Bash(git status:*)\n  - mcp__memory__search",
            )
            self.assertEqual(lint_prompts.check_skills(areas), [])

    def test_bad_samples_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            areas = Path(tmp) / "areas"
            write_skill(areas, "x/skills/no-name/SKILL.md", "description: Does a thing.")
            write_skill(areas, "x/skills/mismatch/SKILL.md", "name: other\ndescription: Does a thing.")
            write_skill(
                areas,
                "x/skills/bad-tool/SKILL.md",
                "name: bad-tool\ndescription: Does a thing.\nallowed-tools: Read, Run",
            )
            write_skill(areas, "x/skills/outer/inner/SKILL.md", "name: inner\ndescription: Nested.")
            no_fm = areas / "x/skills/no-frontmatter/SKILL.md"
            no_fm.parent.mkdir(parents=True)
            no_fm.write_text("# Skill: none\n", encoding="utf-8")

            report = "\n".join(lint_prompts.check_skills(areas))

        self.assertIn("no-name/SKILL.md: missing `name`", report)
        self.assertIn("`name: other` must equal directory name `mismatch`", report)
        self.assertIn("invalid `allowed-tools` entries: Run", report)
        self.assertIn("outer/inner/SKILL.md: SKILL.md must live exactly at skills/<dir>/SKILL.md", report)
        self.assertIn("no-frontmatter/SKILL.md: missing YAML front matter", report)


if __name__ == "__main__":
    unittest.main()
