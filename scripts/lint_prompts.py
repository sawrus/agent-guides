#!/usr/bin/env python3
"""Format checks for skills (Claude Code skill format) and workflow selection blocks.

The file keeps its historical name; prompt files are no longer checked or installed.
"""
from __future__ import annotations

import argparse
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AREAS = ROOT / "areas"
# JEV builds workflow options with this parser; linting with it keeps both readings identical.
JEV_QUESTIONS = ROOT / "extensions/codex/hooks/jev/questions.py"
SELECTION_KEYS = frozenset({"general", "use-when", "avoid-when"})
SELECTION_TEXT_MAX = 300

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SKILL_NAME_MAX = 64
SKILL_DESCRIPTION_MAX = 1024
CLAUDE_TOOLS = frozenset({
    "Read", "Write", "Edit", "Glob", "Grep", "Bash", "WebFetch", "WebSearch",
    "NotebookEdit", "Agent", "TodoWrite",
})
TOOL_PATTERN_RE = re.compile(r"^(Bash\(.+\)|mcp__[A-Za-z0-9_-]+(__[A-Za-z0-9_*-]+)?)$")
FRONTMATTER_KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$")


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> dict[str, object] | None:
    """Parse the flat `key: value` / `key:` + `- item` subset used by skill front matter."""
    match = FRONTMATTER.match(text)
    if not match:
        return None
    data: dict[str, object] = {}
    current_list: list[str] | None = None
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s+-\s*(.*)$", line)
        if item and current_list is not None:
            current_list.append(_unquote(item.group(1)))
            continue
        pair = FRONTMATTER_KEY_RE.match(line)
        if not pair:
            raise ValueError(f"unparseable front matter line: {line!r}")
        key, value = pair.group(1), pair.group(2).strip()
        if value:
            data[key] = _unquote(value)
            current_list = None
        else:
            current_list = []
            data[key] = current_list
    return data


def _split_tools(raw: object) -> list[str]:
    if isinstance(raw, list):
        return [str(t).strip() for t in raw if str(t).strip()]
    return [t.strip() for t in re.split(r",(?![^()]*\))", str(raw)) if t.strip()]


def check_skills(areas: Path) -> list[str]:
    """Return Claude Code skill-format issues for every SKILL.md under `areas`."""
    issues: list[str] = []
    base = areas.parent
    for path in sorted(areas.glob("**/SKILL.md")):
        rel = path.relative_to(base)
        if path.parent.parent.name != "skills":
            issues.append(f"{rel}: SKILL.md must live exactly at skills/<dir>/SKILL.md (nested or misplaced)")
            continue
        try:
            fm = parse_frontmatter(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            issues.append(f"{rel}: {exc}")
            continue
        if fm is None:
            issues.append(f"{rel}: missing YAML front matter (`---` ... `---`)")
            continue
        dir_name = path.parent.name
        name = fm.get("name")
        if not isinstance(name, str) or not name:
            issues.append(f"{rel}: missing `name`")
        elif name != dir_name:
            issues.append(f"{rel}: `name: {name}` must equal directory name `{dir_name}`")
        elif not SKILL_NAME_RE.match(name) or len(name) > SKILL_NAME_MAX:
            issues.append(f"{rel}: `name` must be kebab-case (a-z, 0-9, -) and <= {SKILL_NAME_MAX} chars")
        description = fm.get("description")
        if not isinstance(description, str) or not description.strip():
            issues.append(f"{rel}: missing non-empty `description`")
        elif len(description) > SKILL_DESCRIPTION_MAX:
            issues.append(f"{rel}: `description` exceeds {SKILL_DESCRIPTION_MAX} chars")
        if "allowed-tools" in fm:
            invalid = [t for t in _split_tools(fm["allowed-tools"])
                       if t not in CLAUDE_TOOLS and not TOOL_PATTERN_RE.match(t)]
            if invalid:
                issues.append(f"{rel}: invalid `allowed-tools` entries: {', '.join(invalid)}")
    return issues


def load_questions():
    spec = importlib.util.spec_from_file_location("jev_questions", JEV_QUESTIONS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def selection_issues(rel: Path, front: dict) -> list[str]:
    """Problems in one workflow's `selection` block (shape and text limits)."""
    selection = front.get("selection")
    if not isinstance(selection, dict):
        return [f"{rel}: missing `selection` block with `general` and `use-when`"]
    issues = [f"{rel}: unknown `selection` key `{key}`" for key in sorted(set(selection) - SELECTION_KEYS)]
    if not isinstance(selection.get("general"), bool):
        issues.append(f"{rel}: `selection.general` must be true or false")
    for key in ("use-when", "avoid-when"):
        value = selection.get(key)
        if key == "avoid-when" and key not in selection:
            continue
        if not isinstance(value, str) or not value.strip() or "{{" in value:
            issues.append(f"{rel}: `selection.{key}` must be a non-empty quoted sentence")
        elif len(value) > SELECTION_TEXT_MAX:
            issues.append(f"{rel}: `selection.{key}` exceeds {SELECTION_TEXT_MAX} chars")
    return issues


def check_workflows(areas: Path) -> list[str]:
    """Every workflow needs `type: workflow` and a valid `selection`; at most one general workflow per top-level area."""
    questions = load_questions()
    issues: list[str] = []
    general: dict[str, list[str]] = {}
    for path in sorted(areas.glob("**/workflows/*.md")):
        rel = path.relative_to(areas.parent)
        front = questions.parse_front(path.read_text(encoding="utf-8"))
        if front.get("type") != "workflow":
            issues.append(f"{rel}: missing `type: workflow`; JEV ignores this file")
            continue
        issues.extend(selection_issues(rel, front))
        if isinstance(front.get("selection"), dict) and front["selection"].get("general") is True:
            general.setdefault(path.relative_to(areas).parts[0], []).append(str(rel))
    for area, paths in sorted(general.items()):
        if len(paths) > 1:
            issues.append(f"areas/{area}: more than one `selection.general: true` workflow: {', '.join(paths)}")
    return issues


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="Exit 1 on any issue")
    args = ap.parse_args()

    # Prompt files are no longer part of the pack (agentic does not install them); only skills and workflows are checked.
    issues: list[str] = []
    issues.extend(check_skills(AREAS))
    issues.extend(check_workflows(AREAS))

    if issues:
        print("Content lint issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1 if args.strict else 0

    print("All skills and workflow selection blocks pass format checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
