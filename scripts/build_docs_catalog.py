#!/usr/bin/env python3
"""Build docs/site/catalog.json from the pack: rules, skills, and workflows of every spec under areas/.

The site (docs/site/app.js) renders this catalog. Python standard library only: frontmatter is parsed with a
small line parser, not PyYAML, so the GitHub Pages job needs no extra packages.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
AREAS_DIR = ROOT / "areas"
CATALOG_VERSION = "1.4.0"
MIN_STEPS = 3

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)
# One request per body line: `Example request: <text>` (bold `**Example request:**` also works); several are allowed.
EXAMPLE_REQUEST_RE = re.compile(r"^\*{0,2}Example request:\*{0,2}\s*(.+?)\s*$", re.MULTILINE)
# A step heading: `### 1. Title` (`##`/`####` and `1)` also work).
STEP_HEADING_RE = re.compile(r"^(#{2,4})\s+(\d+)[.)]\s+(.+?)\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+\S")
# A step field: `- **Do:** text`, `**Do**: text`, `* **Done when:** text`.
STEP_FIELD_RE = re.compile(r"^\s*(?:[-*]\s+)?\*\*(Do|Done when)\s*(?::\*\*|\*\*\s*:)\s*(.*)$", re.IGNORECASE)
H1_RE = re.compile(r"^#\s+.*$", re.MULTILINE)


# --- frontmatter ---------------------------------------------------------------------------------------------

def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'`":
        return value[1:-1].strip()
    return value


def _scalar_or_list(value: str):
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        return [_unquote(x) for x in value[1:-1].split(",") if x.strip()]
    return _unquote(value)


def parse_frontmatter(text: str) -> Tuple[Dict[str, object], str]:
    """Return (frontmatter, body). Supports `key: value`, `key: [a, b]`, block lists, and one nested mapping level."""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    data: Dict[str, object] = {}
    key: Optional[str] = None
    for raw in m.group(1).splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if indent == 0:
            k, _, v = line.partition(":")
            key = k.strip()
            data[key] = _scalar_or_list(v) if v.strip() else None
            continue
        if key is None:
            continue
        if line.startswith("- "):
            current = data.get(key)
            if not isinstance(current, list):
                current = []
                data[key] = current
            current.append(_unquote(line[2:]))
        elif ":" in line:
            current = data.get(key)
            if not isinstance(current, dict):
                current = {}
                data[key] = current
            k, _, v = line.partition(":")
            current[k.strip()] = _scalar_or_list(v)
    return data, text[m.end():]


def _str(front: Dict[str, object], key: str) -> str:
    value = front.get(key)
    return value if isinstance(value, str) else ""


def _list(front: Dict[str, object], key: str) -> List[str]:
    value = front.get(key)
    if isinstance(value, list):
        return [str(x) for x in value if str(x)]
    if isinstance(value, str) and value:
        return [value]
    return []


def _strip_h1(body: str) -> str:
    """Body markdown without the leading `# Title` line; the site prints the name itself."""
    body = body.lstrip("\n")
    first = H1_RE.match(body)
    if first:
        body = body[first.end():]
    return body.strip() + "\n" if body.strip() else ""


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


# --- workflow steps ------------------------------------------------------------------------------------------

def _join_lines(lines: List[str]) -> str:
    """Join the continuation lines of a bullet into markdown; keep nested list items on their own lines."""
    out: List[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if out and not re.match(r"^([-*+]|\d+[.)])\s", s):
            out[-1] = f"{out[-1]} {s}"
        else:
            out.append(s)
    return "\n".join(out).strip()


def parse_steps(body: str) -> List[dict]:
    """Parse `### N. Title` blocks with `**Do:**` and `**Done when:**` bullets. Missing parts stay empty."""
    steps: List[dict] = []
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        head = STEP_HEADING_RE.match(lines[i])
        if not head:
            i += 1
            continue
        level = len(head.group(1))
        block: List[str] = []
        i += 1
        while i < len(lines):
            other = HEADING_RE.match(lines[i])
            if other and len(other.group(1)) <= level:
                break
            block.append(lines[i])
            i += 1
        fields: Dict[str, List[str]] = {}
        name: Optional[str] = None
        for line in block:
            fm = STEP_FIELD_RE.match(line)
            if fm:
                name = "do" if fm.group(1).lower() == "do" else "done_when"
                fields[name] = [fm.group(2)]
            elif name and line.strip():
                # Continuation lines and nested items belong to the last field.
                fields[name].append(line)
        steps.append({
            "title": head.group(3).strip(),
            "do": _join_lines(fields.get("do", [])),
            "done_when": _join_lines(fields.get("done_when", [])),
        })
    return steps


# --- refs ----------------------------------------------------------------------------------------------------

def _resolve_skill(spec: str, name: str) -> Optional[str]:
    for base in (AREAS_DIR / spec / "skills", *sorted(AREAS_DIR.glob(f"{spec.split('/')[0]}/*/skills"))):
        for candidate in (base / name / "SKILL.md", base / f"{name}.md"):
            if candidate.exists():
                return _rel(candidate)
    return None


def _resolve_rule(spec: str, name: str) -> Optional[str]:
    file_name = name if name.endswith(".md") else f"{name}.md"
    for base in (AREAS_DIR / spec / "rules", *sorted(AREAS_DIR.glob(f"{spec.split('/')[0]}/*/rules"))):
        candidate = base / file_name
        if candidate.exists():
            return _rel(candidate)
    return None


# --- items ---------------------------------------------------------------------------------------------------

@dataclass
class Spec:
    spec: str
    summary: str = ""
    agents_path: str = ""
    rules: List[dict] = field(default_factory=list)
    skills: List[dict] = field(default_factory=list)
    workflows: List[dict] = field(default_factory=list)


def _spec_of(path: Path) -> str:
    return "/".join(path.relative_to(AREAS_DIR).parts[:2])


def parse_rule(path: Path) -> dict:
    front, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    return {
        "name": path.stem,
        "description": _str(front, "description"),
        "paths": _list(front, "paths"),
        "trigger": _str(front, "trigger"),
        "path": _rel(path),
        "body": _strip_h1(body),
    }


def parse_skill(path: Path) -> dict:
    front, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    default = path.parent.name if path.name == "SKILL.md" else path.stem
    return {
        "name": _str(front, "name") or default,
        "description": _str(front, "description"),
        "path": _rel(path),
        "body": _strip_h1(body),
    }


def parse_workflow(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    front, body = parse_frontmatter(text)
    if not front:
        raise ValueError(f"No YAML frontmatter: {path}")
    spec = _spec_of(path)
    selection = front.get("selection") if isinstance(front.get("selection"), dict) else {}
    uses_skills = _list(front, "uses-skills")
    related_rules = _list(front, "related-rules")
    steps = parse_steps(body)
    steps_ok = len(steps) >= MIN_STEPS and all(s["do"] and s["done_when"] for s in steps)
    return {
        "trigger": _str(front, "trigger"),
        "name": _str(front, "name") or path.stem,
        "description": _str(front, "description"),
        "workflow_path": _rel(path),
        "use_when": str(selection.get("use-when", "")),
        "avoid_when": str(selection.get("avoid-when", "")),
        "inputs": _list(front, "inputs"),
        "outputs": _list(front, "outputs"),
        "related_rules": related_rules,
        "rule_refs": [{"name": r.removesuffix(".md"), "path": _resolve_rule(spec, r)} for r in related_rules],
        "uses_skills": uses_skills,
        "skill_refs": [{"name": s, "path": _resolve_skill(spec, s)} for s in uses_skills],
        "checks": _list(front, "checks"),
        "artifacts": _list(front, "artifacts"),
        "steps": steps,
        # Raw body only when the steps could not be parsed, so the site can still show the procedure.
        "body": "" if steps_ok else _strip_h1(EXAMPLE_REQUEST_RE.sub("", body)),
        "examples": [_unquote(e.group(1)) for e in EXAMPLE_REQUEST_RE.finditer(body)],
    }


def _spec_summary(path: Path) -> str:
    """First paragraph after the `# Title` of a spec AGENTS.md."""
    if not path.exists():
        return ""
    for para in re.split(r"\n\s*\n", _strip_h1(parse_frontmatter(path.read_text(encoding="utf-8"))[1])):
        para = para.strip()
        if para and not para.startswith(("#", "-", "|", "```")):
            return " ".join(para.split())
    return ""


# --- catalog -------------------------------------------------------------------------------------------------

def _validate(spec: Spec, require_examples: bool) -> List[str]:
    problems: List[str] = []
    for rule in spec.rules:
        if not rule["description"]:
            problems.append(f"rule missing description: {rule['path']}")
        if not rule["paths"] and rule["trigger"] not in ("manual", "always_on"):
            problems.append(f"rule has neither paths nor trigger: manual: {rule['path']}")
    for skill in spec.skills:
        if not skill["description"]:
            problems.append(f"skill missing description: {skill['path']}")
    for wf in spec.workflows:
        where = wf["workflow_path"]
        if not wf["trigger"]:
            problems.append(f"workflow missing trigger: {where}")
        if not wf["description"]:
            problems.append(f"workflow missing description: {where}")
        if len(wf["steps"]) < MIN_STEPS:
            problems.append(f"workflow has {len(wf['steps'])} parsed steps, needs >= {MIN_STEPS}: {where}")
        for n, step in enumerate(wf["steps"], 1):
            if not step["do"] or not step["done_when"]:
                problems.append(f"workflow step {n} lacks **Do:** or **Done when:**: {where}")
        for ref in wf["rule_refs"] + wf["skill_refs"]:
            if not ref["path"]:
                problems.append(f"workflow references unknown rule or skill `{ref['name']}`: {where}")
        if require_examples and not wf["examples"]:
            problems.append(f"workflow has no `Example request:` line: {where}")
    return problems


def build_catalog(validate: bool = False, require_examples: bool = False) -> Tuple[dict, List[str]]:
    specs: Dict[str, Spec] = {}

    def spec_for(path: Path) -> Spec:
        name = _spec_of(path)
        return specs.setdefault(name, Spec(spec=name))

    for path in sorted(AREAS_DIR.glob("*/*/rules/*.md")):
        spec_for(path).rules.append(parse_rule(path))
    for path in sorted(AREAS_DIR.glob("*/*/skills/*/SKILL.md")):
        spec_for(path).skills.append(parse_skill(path))
    for path in sorted(AREAS_DIR.glob("*/*/workflows/*.md")):
        spec_for(path).workflows.append(parse_workflow(path))

    problems: List[str] = []
    areas_out: List[dict] = []
    for name in sorted(specs):
        spec = specs[name]
        agents = AREAS_DIR / name / "AGENTS.md"
        problems.extend(_validate(spec, require_examples))
        group, _, section = name.partition("/")
        areas_out.append({
            "area": name,
            "group": group,
            "spec": section,
            "summary": _spec_summary(agents),
            "agents_path": _rel(agents) if agents.exists() else "",
            "rules": spec.rules,
            "skills": spec.skills,
            "workflows": sorted(spec.workflows, key=lambda w: w["name"]),
        })

    all_wf = [wf for a in areas_out for wf in a["workflows"]]
    catalog = {
        "version": CATALOG_VERSION,
        "generated_from": "areas/*/*/{rules,skills,workflows}",
        "areas": areas_out,
        "stats": {
            "rules": sum(len(a["rules"]) for a in areas_out),
            "skills": sum(len(a["skills"]) for a in areas_out),
            "workflows": len(all_wf),
            "examples": sum(len(wf["examples"]) for wf in all_wf),
            "problems": len(problems),
        },
    }
    return catalog, problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "docs/site/catalog.json"))
    parser.add_argument("--validate", action="store_true",
                        help="Exit 1 on problems: rules without description or scope, workflows with < 3 steps")
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
