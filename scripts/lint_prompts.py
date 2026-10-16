#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AREAS = ROOT / "areas"

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
WORKFLOW_KEY = re.compile(r"^workflow:\s*([a-z0-9][a-z0-9-]*)\s*$", re.MULTILINE)
PROMPT_HEADER = re.compile(r"^#\s*Prompt:\s*`?([^`\n]+)`?", re.MULTILINE)
USE_WHEN = re.compile(r"^Use when:\s*.+$", re.MULTILINE)
EXAMPLE_BLOCK = re.compile(r"##\s*Example\s*\d+\s*[—-]\s*.+?", re.MULTILINE)
EN_BLOCK = re.compile(r"\*\*EN:\*\*\s*\n```\n.+?\n```", re.DOTALL)
RU_BLOCK = re.compile(r"\*\*RU:\*\*\s*\n```\n.+?\n```", re.DOTALL)
COMMAND_REF_RE = re.compile(r"(?m)^/([a-z0-9][a-z0-9-]*)\b")
PLACEHOLDER_STRINGS = (
    "<project context>",
    "<контекст проекта>",
    "Objective: clearly state",
    "Goal: execute workflow steps end-to-end",
    "Use when: run workflow",
)


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


def workflow_stems_for_prompt(prompt_path: Path) -> set[str]:
    wf_dir = prompt_path.parent.parent / "workflows"
    if not wf_dir.exists():
        return set()
    return {p.stem for p in wf_dir.glob("*.md")}


def parse_workflow_key(text: str) -> str | None:
    frontmatter = FRONTMATTER.match(text)
    if not frontmatter:
        return None
    match = WORKFLOW_KEY.search(frontmatter.group(1))
    if not match:
        return None
    return match.group(1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="Exit 1 on any issue")
    args = ap.parse_args()

    issues: list[str] = []
    for path in sorted(AREAS.glob("**/prompts/*.md")):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)

        workflow = parse_workflow_key(text)
        if workflow is None:
            issues.append(f"{rel}: missing prompt front matter with `workflow: <workflow-stem>`")

        header = PROMPT_HEADER.search(text)
        if not header:
            issues.append(f"{rel}: missing `# Prompt:` header")
            continue

        header_command = header.group(1).strip()
        if workflow and header_command != f"/{workflow}":
            issues.append(f"{rel}: prompt header must equal `/{workflow}`")
        if not USE_WHEN.search(text):
            issues.append(f"{rel}: missing `Use when:` section")
        example_count = len(EXAMPLE_BLOCK.findall(text))
        if not example_count:
            issues.append(f"{rel}: missing `## Example N — ...` block")
        elif example_count < 2 or example_count > 3:
            issues.append(f"{rel}: example count must be 2 or 3 (found {example_count})")
        if not EN_BLOCK.search(text):
            issues.append(f"{rel}: missing EN fenced block")
        if not RU_BLOCK.search(text):
            issues.append(f"{rel}: missing RU fenced block")
        if len(EN_BLOCK.findall(text)) != example_count:
            issues.append(f"{rel}: EN block count must match example count")
        if len(RU_BLOCK.findall(text)) != example_count:
            issues.append(f"{rel}: RU block count must match example count")
        if "Workflow link command:" in text:
            issues.append(f"{rel}: legacy `Workflow link command:` block is not allowed")
        if any(token in text for token in PLACEHOLDER_STRINGS):
            issues.append(f"{rel}: placeholder or generic scaffold text remains")
        if workflow and path.stem != workflow:
            issues.append(f"{rel}: prompt filename must match workflow stem `{workflow}`")

        refs = {m.group(1) for m in COMMAND_REF_RE.finditer(text)}
        area_stems = workflow_stems_for_prompt(path)
        if workflow:
            if workflow not in area_stems:
                issues.append(f"{rel}: workflow `{workflow}` not found in sibling workflows/")
            if not refs:
                issues.append(f"{rel}: no /<workflow-file-name> command reference found")
            elif refs != {workflow}:
                issues.append(f"{rel}: all slash commands must be canonical `/{workflow}` (found: {', '.join(sorted(refs))})")
        elif area_stems and not (refs & area_stems):
            issues.append(f"{rel}: no /<workflow-file-name> command reference found")

    issues.extend(check_skills(AREAS))

    if issues:
        print("Prompt lint issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1 if args.strict else 0

    print("All prompts and skills pass format checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
