#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
AREAS_DIR = ROOT / "areas"

WORKFLOW_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
TRIGGER_RE = re.compile(r"^trigger:\s*(.+)$", re.MULTILINE)
NAME_RE = re.compile(r"^name:\s*(.+)$", re.MULTILINE)
DESC_RE = re.compile(r"^description:\s*(.+)$", re.MULTILINE)
USE_WHEN_RE = re.compile(r"^\s+use-when:\s*(.+)$", re.MULTILINE)
# One request per body line: `Example request: <text>` (bold `**Example request:**` also works); several are allowed.
EXAMPLE_REQUEST_RE = re.compile(r"^\*{0,2}Example request:\*{0,2}\s*(.+?)\s*$", re.MULTILINE)
WORKFLOW_DIAGRAM_RE = re.compile(
    r"<!-- agent-diagram:start -->\n```mermaid\n(.*?)\n```\n<!-- agent-diagram:end -->",
    re.DOTALL,
)


def _parse_yaml_list(frontmatter: str, key: str) -> List[str]:
    m = re.search(rf"^{re.escape(key)}:\s*\n((?:\s*-\s.*\n)+)", frontmatter, re.MULTILINE)
    if not m:
        inline = re.search(rf"^{re.escape(key)}:\s*\[(.*?)\]\s*$", frontmatter, re.MULTILINE)
        if not inline:
            return []
        return [x.strip().strip("'\"") for x in inline.group(1).split(",") if x.strip()]
    return [line.strip()[1:].strip().strip("'\"") for line in m.group(1).splitlines() if line.strip().startswith("-")]


def _area_and_stem(path: Path) -> tuple[str, str]:
    rel = path.relative_to(ROOT)
    parts = rel.parts
    return "/".join(parts[1:3]), path.stem


def _resolve_skill_paths(area: str, uses_skills: List[str]) -> List[dict]:
    base = ROOT / "areas" / area / "skills"
    resolved: List[dict] = []
    for name in uses_skills:
        c1 = base / name / "SKILL.md"
        c2 = base / f"{name}.md"
        path = c1 if c1.exists() else c2 if c2.exists() else None
        resolved.append({"name": name, "path": str(path.relative_to(ROOT)) if path else None})
    return resolved


@dataclass
class Workflow:
    key: str
    area: str
    stem: str
    trigger: str
    name: str
    description: str
    path: str
    inputs: List[str]
    outputs: List[str]
    roles: List[str]
    related_rules: List[str]
    uses_skills: List[str]
    quality_gates: List[str]
    skill_refs: List[dict]
    workflow_diagram: str
    use_when: str
    examples: List[str]


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'`":
        return value[1:-1].strip()
    return value


def parse_workflow(path: Path) -> Workflow:
    text = path.read_text(encoding="utf-8")
    m = WORKFLOW_RE.search(text)
    if not m:
        raise ValueError(f"No YAML frontmatter: {path}")
    front = m.group(1)
    trig = TRIGGER_RE.search(front)
    name = NAME_RE.search(front)
    desc = DESC_RE.search(front)
    area, stem = _area_and_stem(path)
    uses_skills = _parse_yaml_list(front, "uses-skills")

    return Workflow(
        key=f"{area}:{stem}",
        area=area,
        stem=stem,
        trigger=trig.group(1).strip() if trig else "",
        name=name.group(1).strip() if name else path.stem,
        description=desc.group(1).strip() if desc else "",
        path=str(path.relative_to(ROOT)),
        inputs=_parse_yaml_list(front, "inputs"),
        outputs=_parse_yaml_list(front, "outputs"),
        roles=_parse_yaml_list(front, "roles"),
        related_rules=_parse_yaml_list(front, "related-rules"),
        uses_skills=uses_skills,
        quality_gates=_parse_yaml_list(front, "quality-gates"),
        skill_refs=_resolve_skill_paths(area, uses_skills),
        workflow_diagram=_extract_workflow_diagram(text),
        use_when=_unquote(use_when.group(1)) if (use_when := USE_WHEN_RE.search(front)) else "",
        examples=[_unquote(e.group(1)) for e in EXAMPLE_REQUEST_RE.finditer(text, m.end())],
    )


def _extract_workflow_diagram(text: str) -> str:
    match = WORKFLOW_DIAGRAM_RE.search(text)
    return match.group(1).strip() if match else ""


def build_catalog(validate: bool = False, require_examples: bool = False) -> Tuple[dict, List[str]]:
    workflows: List[Workflow] = []
    problems: List[str] = []

    for path in sorted(AREAS_DIR.glob("**/workflows/*.md")):
        wf = parse_workflow(path)
        workflows.append(wf)
        if not wf.trigger:
            problems.append(f"workflow missing trigger: {wf.path}")
        if require_examples and not wf.examples:
            problems.append(f"workflow has no `Example request:` line: {wf.path}")

    areas_out: Dict[str, dict] = {}
    for wf in sorted(workflows, key=lambda x: (x.area, x.stem)):
        bucket = areas_out.setdefault(wf.area, {"area": wf.area, "workflows": []})
        bucket["workflows"].append(
            {
                "trigger": wf.trigger,
                "name": wf.name,
                "description": wf.description,
                "workflow_path": wf.path,
                "use_when": wf.use_when,
                "inputs": wf.inputs,
                "outputs": wf.outputs,
                "roles": wf.roles,
                "related_rules": wf.related_rules,
                "uses_skills": wf.uses_skills,
                "skill_refs": wf.skill_refs,
                "quality_gates": wf.quality_gates,
                "workflow_diagram": wf.workflow_diagram,
                "examples": wf.examples,
            }
        )

    catalog = {
        "version": "1.3.0",
        "generated_from": "areas/**/workflows",
        "areas": list(areas_out.values()),
        "stats": {
            "workflows": len(workflows),
            "examples": sum(len(wf.examples) for wf in workflows),
            "problems": len(problems),
        },
    }
    return catalog, problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "docs/site/catalog.json"))
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--require-examples", action="store_true",
                        help="Report workflows without an `Example request:` line as problems")
    args = parser.parse_args()

    catalog, problems = build_catalog(validate=args.validate, require_examples=args.require_examples)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if problems:
        print("Catalog validation issues:")
        for issue in problems:
            print(f"- {issue}")

    return 1 if args.validate and problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
