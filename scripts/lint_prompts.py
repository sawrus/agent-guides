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


    if issues:
        print("Prompt lint issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1 if args.strict else 0

    print("All prompts pass format checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
