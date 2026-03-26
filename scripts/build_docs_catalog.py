#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
AREAS_DIR = ROOT / "areas"

WORKFLOW_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
TRIGGER_RE = re.compile(r"^trigger:\s*(.+)$", re.MULTILINE)
NAME_RE = re.compile(r"^name:\s*(.+)$", re.MULTILINE)
DESC_RE = re.compile(r"^description:\s*(.+)$", re.MULTILINE)
PROMPT_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
PROMPT_WORKFLOW_RE = re.compile(r"^workflow:\s*([a-z0-9][a-z0-9-]*)\s*$", re.MULTILINE)
PROMPT_TITLE_RE = re.compile(r"^#\s*Prompt:\s*`?([^`\n]+)`?", re.MULTILINE)
USE_WHEN_RE = re.compile(r"^Use when:\s*(.+)$", re.MULTILINE)
EXAMPLE_RE = re.compile(
    r"##\s*Example\s*(\d+)\s*[—-]\s*(.*?)\n.*?\*\*EN:\*\*\s*\n```\n(.*?)\n```\s*\n\s*\*\*RU:\*\*\s*\n```\n(.*?)\n```",
    re.DOTALL,
)
COMMAND_REF_RE = re.compile(r"(?m)^/([a-z0-9][a-z0-9-]*)\b")
PLACEHOLDER_STRINGS = (
    "<project context>",
    "<контекст проекта>",
    "Objective: clearly state",
    "Goal: execute workflow steps end-to-end",
    "Use when: run workflow",
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


@dataclass
class Example:
    number: int
    title: str
    en: str
    ru: str


@dataclass
class Prompt:
    key: str
    area: str
    stem: str
    workflow: str
    trigger: str
    path: str
    use_when: str
    examples: List[Example]
    command_refs: List[str]


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
    )


def parse_prompt(path: Path) -> Prompt:
    text = path.read_text(encoding="utf-8")
    frontmatter = PROMPT_FRONTMATTER_RE.match(text)
    workflow = ""
    if frontmatter:
        workflow_match = PROMPT_WORKFLOW_RE.search(frontmatter.group(1))
        if workflow_match:
            workflow = workflow_match.group(1).strip()
    t = PROMPT_TITLE_RE.search(text)
    uw = USE_WHEN_RE.search(text)
    examples = [
        Example(number=int(m.group(1)), title=m.group(2).strip(), en=m.group(3).strip(), ru=m.group(4).strip())
        for m in EXAMPLE_RE.finditer(text)
    ]
    area, stem = _area_and_stem(path)
    refs = sorted({m.group(1) for m in COMMAND_REF_RE.finditer(text)})
    return Prompt(
        key=f"{area}:{stem}",
        area=area,
        stem=stem,
        workflow=workflow,
        trigger=t.group(1).strip() if t else "",
        path=str(path.relative_to(ROOT)),
        use_when=uw.group(1).strip() if uw else "",
        examples=examples,
        command_refs=refs,
    )


def _match_prompt_to_workflow(prompt: Prompt, workflows_by_area: Dict[str, Dict[str, Workflow]]) -> Workflow | None:
    area_wf = workflows_by_area.get(prompt.area, {})
    if prompt.workflow:
        return area_wf.get(prompt.workflow)
    return None


def build_catalog(validate: bool = False) -> Tuple[dict, List[str]]:
    workflows_by_area: Dict[str, Dict[str, Workflow]] = {}
    prompts: List[Prompt] = []
    problems: List[str] = []
    prompts_by_workflow: Dict[tuple[str, str], Prompt] = {}

    for path in sorted(AREAS_DIR.glob("**/workflows/*.md")):
        wf = parse_workflow(path)
        workflows_by_area.setdefault(wf.area, {})[wf.stem] = wf
        if not wf.trigger:
            problems.append(f"workflow missing trigger: {wf.path}")

    for path in sorted(AREAS_DIR.glob("**/prompts/*.md")):
        pr = parse_prompt(path)
        prompts.append(pr)
        if not pr.trigger:
            problems.append(f"prompt missing trigger: {pr.path}")
        if not pr.workflow:
            problems.append(f"prompt missing front matter workflow key: {pr.path}")
        if pr.workflow and pr.stem != pr.workflow:
            problems.append(f"prompt filename must match workflow stem: {pr.path}")
        if pr.workflow and pr.trigger != f"/{pr.workflow}":
            problems.append(f"prompt header must match workflow stem: {pr.path}")
        if not pr.examples:
            problems.append(f"prompt has no EN/RU examples: {pr.path}")
        if len(pr.examples) < 2 or len(pr.examples) > 3:
            problems.append(f"prompt example count must be 2 or 3: {pr.path}")
        if "Workflow link command:" in path.read_text(encoding="utf-8"):
            problems.append(f"legacy workflow link block not allowed: {pr.path}")
        if any(token in path.read_text(encoding="utf-8") for token in PLACEHOLDER_STRINGS):
            problems.append(f"placeholder scaffold text not allowed: {pr.path}")
        if pr.workflow and pr.command_refs and set(pr.command_refs) != {pr.workflow}:
            problems.append(f"prompt contains non-canonical slash commands: {pr.path}")
        if pr.workflow:
            key = (pr.area, pr.workflow)
            if key in prompts_by_workflow:
                problems.append(f"multiple prompts mapped to workflow {pr.area}/{pr.workflow}: {pr.path}")
            else:
                prompts_by_workflow[key] = pr

    matched_prompt_keys: set[str] = set()
    prompt_by_workflow_key: Dict[str, Prompt] = {}
    for pr in prompts:
        wf = _match_prompt_to_workflow(pr, workflows_by_area)
        if wf:
            prompt_by_workflow_key[wf.key] = pr
            matched_prompt_keys.add(pr.key)
        elif validate:
            problems.append(f"prompt not matched to workflow via front matter: {pr.path}")

    if validate:
        all_workflows = [wf for area in workflows_by_area.values() for wf in area.values()]
        for wf in all_workflows:
            if wf.key not in prompt_by_workflow_key:
                problems.append(f"workflow has no matched prompt: {wf.path}")

    areas_out: Dict[str, dict] = {}
    all_workflows = [wf for area in workflows_by_area.values() for wf in area.values()]
    for wf in sorted(all_workflows, key=lambda x: (x.area, x.stem)):
        pr = prompt_by_workflow_key.get(wf.key)
        bucket = areas_out.setdefault(wf.area, {"area": wf.area, "workflows": []})
        bucket["workflows"].append(
            {
                "trigger": wf.trigger,
                "name": wf.name,
                "description": wf.description,
                "workflow_path": wf.path,
                "prompt_path": pr.path if pr else None,
                "prompt_command_refs": pr.command_refs if pr else [],
                "use_when": pr.use_when if pr else "",
                "inputs": wf.inputs,
                "outputs": wf.outputs,
                "roles": wf.roles,
                "related_rules": wf.related_rules,
                "uses_skills": wf.uses_skills,
                "skill_refs": wf.skill_refs,
                "quality_gates": wf.quality_gates,
                "examples": {"both": [asdict(e) for e in (pr.examples if pr else [])]},
            }
        )

    catalog = {
        "version": "1.1.0",
        "generated_from": "areas/**/{workflows,prompts}",
        "areas": list(areas_out.values()),
        "stats": {
            "workflows": len(all_workflows),
            "prompts": len(prompts),
            "matched_prompts": len(matched_prompt_keys),
            "problems": len(problems),
        },
    }
    return catalog, problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "docs/site/catalog.json"))
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    catalog, problems = build_catalog(validate=args.validate)
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
