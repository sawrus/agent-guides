#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
AREAS_DIR = ROOT / "areas"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
TRIGGER_RE = re.compile(r"^trigger:\s*(.+)$", re.MULTILINE)
INITIATOR_RE = re.compile(r"^\s{2}initiator:\s*(.+)$", re.MULTILINE)
STEP_HEADING_RE = re.compile(r"^(?:###\s+|(?=\d+\.\s+))(.*)$", re.MULTILINE)
H2_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
ROLE_MENTION_RE = re.compile(r"`@([^`]+)`")
GENERATED_SECTION_RE = re.compile(
    r"\n?## Agent Interaction Diagram\n\n"
    r"<!-- agent-diagram:start -->\n"
    r"```mermaid\n.*?\n```\n"
    r"<!-- agent-diagram:end -->\n?",
    re.DOTALL,
)


@dataclass
class Step:
    label: str
    roles: list[str]


def _parse_yaml_list(frontmatter: str, key: str) -> list[str]:
    m = re.search(rf"^{re.escape(key)}:\s*\n((?:\s*-\s.*\n)+)", frontmatter, re.MULTILINE)
    if not m:
        inline = re.search(rf"^{re.escape(key)}:\s*\[(.*?)\]\s*$", frontmatter, re.MULTILINE)
        if not inline:
            return []
        return [x.strip().strip("'\"") for x in inline.group(1).split(",") if x.strip()]
    return [line.strip()[1:].strip().strip("'\"") for line in m.group(1).splitlines() if line.strip().startswith("-")]


def _clean_role(role: str) -> str:
    return role.strip().strip("'\"").removeprefix("@").strip()


def _clean_step_label(raw: str) -> str:
    label = re.sub(r"\s+[—-]\s+`@[^`]+`(?:\s*\+\s*`@[^`]+`)*.*$", "", raw).strip()
    label = re.sub(r"`@[^`]+`", "", label).strip()
    label = re.sub(r"^Step\s+", "", label, flags=re.IGNORECASE)
    return label


def _extract_steps(text: str, fallback_roles: list[str]) -> list[Step]:
    steps: list[Step] = []
    for match in STEP_HEADING_RE.finditer(text):
        heading = match.group(1).strip()
        roles = [_clean_role(role) for role in ROLE_MENTION_RE.findall(heading)]
        roles = [role for role in roles if role]
        steps.append(Step(label=_clean_step_label(heading), roles=roles or fallback_roles))
    return steps


def _extract_exit(text: str) -> str:
    match = re.search(r"^## Exit\n\n?(.+?)(?:\n## |\Z)", text, re.MULTILINE | re.DOTALL)
    if not match:
        return "Workflow complete"
    first_line = next((line.strip() for line in match.group(1).splitlines() if line.strip()), "")
    return first_line or "Workflow complete"


def _has_loop(text: str) -> bool:
    return bool(re.search(r"^##\s+(Iteration Loop|Rollback|Rollbacks?)\b", text, re.MULTILINE))


def _node_id(prefix: str, index: int) -> str:
    return f"{prefix}_{index}"


def _mermaid_label(value: str, max_len: int = 78) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    compact = compact.replace("`", "").replace("**", "")
    if len(compact) > max_len:
        compact = compact[: max_len - 3].rstrip() + "..."
    return compact.replace("\\", "\\\\").replace('"', '\\"')


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def build_diagram(text: str) -> str:
    front = FRONTMATTER_RE.search(text)
    frontmatter = front.group(1) if front else ""
    trigger = TRIGGER_RE.search(frontmatter)
    initiator = INITIATOR_RE.search(frontmatter)

    trigger_label = trigger.group(1).strip() if trigger else "/workflow"
    roles = [_clean_role(role) for role in _parse_yaml_list(frontmatter, "roles")]
    if initiator:
        roles = _unique([_clean_role(initiator.group(1)), *roles])
    steps = _extract_steps(text, roles)

    lines = ["flowchart TD", f'  start(["Start { _mermaid_label(trigger_label) }"])']
    role_ids: dict[str, str] = {}
    for index, role in enumerate(_unique(role for step in steps for role in step.roles), 1):
        role_id = _node_id("role", index)
        role_ids[role] = role_id
        lines.append(f'  {role_id}["{_mermaid_label(role)}"]')

    if steps:
        for index, step in enumerate(steps, 1):
            lines.append(f'  step_{index}["{_mermaid_label(step.label)}"]')
        lines.append(f'  exit(["{_mermaid_label(_extract_exit(text))}"])')
        lines.append("  start --> step_1")
        for index in range(1, len(steps)):
            lines.append(f"  step_{index} --> step_{index + 1}")
        lines.append(f"  step_{len(steps)} --> exit")
        for index, step in enumerate(steps, 1):
            for role in step.roles:
                role_id = role_ids.get(role)
                if role_id:
                    lines.append(f"  {role_id} -. owns .-> step_{index}")
        if _has_loop(text) and len(steps) > 1:
            lines.append(f"  step_{len(steps)} -. iterate if blocked .-> step_1")
    else:
        lines.append(f'  exit(["{_mermaid_label(_extract_exit(text))}"])')
        lines.append("  start --> exit")
        for role, role_id in role_ids.items():
            lines.append(f"  {role_id} -. owns .-> exit")

    return "\n".join(lines)


def _section(diagram: str) -> str:
    return (
        "## Agent Interaction Diagram\n\n"
        "<!-- agent-diagram:start -->\n"
        "```mermaid\n"
        f"{diagram}\n"
        "```\n"
        "<!-- agent-diagram:end -->\n"
    )


def _insert_index(text: str) -> int:
    text_without_existing = GENERATED_SECTION_RE.sub("\n", text)
    candidates = []
    for match in H2_RE.finditer(text_without_existing):
        heading = match.group(1).strip().lower()
        if heading.startswith(("iteration loop", "rollback", "exit", "mandatory role delegation")):
            candidates.append(match.start())
    if candidates:
        return candidates[0]
    return len(text_without_existing.rstrip()) + 1


def sync_text(text: str) -> str:
    diagram = build_diagram(text)
    text = GENERATED_SECTION_RE.sub("\n", text).rstrip() + "\n"
    section = _section(diagram)
    idx = _insert_index(text)
    before = text[:idx].rstrip()
    after = text[idx:].lstrip("\n")
    if after:
        return f"{before}\n\n{section}\n{after}"
    return f"{before}\n\n{section}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if any workflow diagram is out of date.")
    args = parser.parse_args()

    changed: list[Path] = []
    for path in sorted(AREAS_DIR.glob("**/workflows/*.md")):
        original = path.read_text(encoding="utf-8")
        updated = sync_text(original)
        if updated != original:
            changed.append(path)
            if not args.check:
                path.write_text(updated, encoding="utf-8")

    if changed:
        for path in changed:
            print(path.relative_to(ROOT))
        return 1 if args.check else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
