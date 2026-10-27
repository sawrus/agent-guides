#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
AREAS = ROOT / "areas"

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
LIST_ITEM = re.compile(r"^\s*-\s+(.+?)\s*$", re.MULTILINE)
# Same line format as scripts/build_docs_catalog.py.
EXAMPLE_REQUEST = re.compile(r"^\*{0,2}Example request:\*{0,2}\s*\S", re.MULTILINE)


@dataclass
class Finding:
    severity: str
    message: str
    path: str


@dataclass
class Score:
    specialization: str
    environment: str
    score: int
    dimensions: dict[str, int]
    findings: list[Finding]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(path: Path) -> str:
    match = FRONTMATTER.match(read(path))
    return match.group(1) if match else ""


def yaml_list(front: str, key: str) -> list[str]:
    match = re.search(rf"^{re.escape(key)}:\s*\n((?:\s*-\s.*\n?)+)", front, re.MULTILINE)
    if not match:
        return []
    return [x.strip().strip("'\"") for x in LIST_ITEM.findall(match.group(1))]


def has_key(front: str, key: str) -> bool:
    return re.search(rf"^{re.escape(key)}:\s*.+$", front, re.MULTILINE) is not None


def declares(front: str, key: str) -> bool:
    return re.search(rf"^{re.escape(key)}:", front, re.MULTILINE) is not None


def spec_dirs() -> Iterable[Path]:
    for area in sorted(AREAS.iterdir()):
        if not area.is_dir() or area.name == "template":
            continue
        for spec in sorted(area.iterdir()):
            if spec.is_dir():
                yield spec


def bounded(value: int) -> int:
    return max(0, min(100, value))


def assess_spec(spec: Path, environment: str) -> Score:
    rel_spec = spec.relative_to(ROOT).as_posix()
    findings: list[Finding] = []
    dimensions = {
        "structure": 100,
        "reference_integrity": 100,
        "sdlc_coverage": 100,
        "workflow_contract": 100,
        "example_usefulness": 100,
        "environment_compatibility": 100,
        "token_efficiency": 100,
    }

    # Prompt files are no longer part of the pack; workflows carry `Example request:` lines instead.
    required_dirs = ["rules", "skills", "workflows"]
    if not (spec / "AGENTS.md").exists():
        findings.append(Finding("error", "missing specialization AGENTS.md", rel_spec))
        dimensions["structure"] -= 35
    for name in required_dirs:
        if not (spec / name).is_dir():
            findings.append(Finding("error", f"missing {name}/ directory", rel_spec))
            dimensions["structure"] -= 15

    skills = {p.parent.name for p in spec.glob("skills/*/SKILL.md")}
    workflows = sorted(spec.glob("workflows/*.md"))
    rules = sorted(spec.glob("rules/*.md"))

    if len(skills) > 6:
        findings.append(Finding("warn", f"skill count is {len(skills)}; target is <= 6 for token efficiency", rel_spec))
        dimensions["token_efficiency"] -= min(40, (len(skills) - 6) * 8)
    if len(rules) > 12:
        findings.append(Finding("warn", f"rule count is {len(rules)}; consider consolidating always-loaded guidance", rel_spec))
        dimensions["token_efficiency"] -= min(30, (len(rules) - 12) * 3)

    missing_examples = 0
    for workflow in workflows:
        rel = workflow.relative_to(ROOT).as_posix()
        front = frontmatter(workflow)
        for key in ["name", "type", "trigger", "description"]:
            if not has_key(front, key):
                findings.append(Finding("error", f"workflow missing `{key}` front matter", rel))
                dimensions["reference_integrity"] -= 5
        # docs/artifact-standard.md ART-W1: selection, uses-skills, related-rules; no roles or initiator.
        for key in ["selection", "uses-skills", "related-rules"]:
            if not declares(front, key):
                findings.append(Finding("warn", f"workflow missing `{key}` front matter (ART-W1)", rel))
                dimensions["workflow_contract"] -= 5
        for key in ["roles", "agent", "execution"]:
            if declares(front, key):
                findings.append(Finding("warn", f"workflow declares `{key}`; the standard has no roles (ART-W1)", rel))
                dimensions["workflow_contract"] -= 5
        for skill in yaml_list(front, "uses-skills"):
            if skill not in skills:
                findings.append(Finding("error", f"uses missing skill `{skill}`", rel))
                dimensions["reference_integrity"] -= 12

        body = read(workflow)
        if not EXAMPLE_REQUEST.search(body):
            findings.append(Finding("warn", "workflow has no `Example request:` line", rel))
            missing_examples += 1
        text = body.lower()
        for phase in ["**do", "**done when"]:
            if phase not in text:
                findings.append(Finding("warn", f"workflow steps lack `{phase.strip('*')}` (ART-W2)", rel))
                dimensions["sdlc_coverage"] -= 5

    dimensions["example_usefulness"] -= min(30, missing_examples * 5)

    agent_text = read(spec / "AGENTS.md") if (spec / "AGENTS.md").exists() else ""
    if environment == "opencode" and "skills/*/SKILL.md" not in agent_text:
        findings.append(Finding("warn", "AGENTS.md does not describe skill loading for opencode-compatible layouts", rel_spec))
        dimensions["environment_compatibility"] -= 10

    dimensions = {k: bounded(v) for k, v in dimensions.items()}
    score = round(sum(dimensions.values()) / len(dimensions))
    return Score(
        specialization=rel_spec,
        environment=environment,
        score=score,
        dimensions=dimensions,
        findings=findings,
    )


def markdown_report(scores: list[Score]) -> str:
    lines = ["# Agentic Area Quality Report", ""]
    for score in scores:
        lines.append(f"## {score.specialization} ({score.environment})")
        lines.append("")
        lines.append(f"Score: **{score.score}/100**")
        lines.append("")
        lines.append("| Dimension | Score |")
        lines.append("|---|---:|")
        for name, value in score.dimensions.items():
            lines.append(f"| {name} | {value} |")
        lines.append("")
        if score.findings:
            lines.append("Findings:")
            for finding in score.findings:
                lines.append(f"- [{finding.severity}] `{finding.path}`: {finding.message}")
        else:
            lines.append("Findings: none")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", default="all", choices=["all", "codex", "opencode", "claude", "gemini", "antigravity", "cursor"])
    parser.add_argument("--json-output", default="reports/area-quality.json")
    parser.add_argument("--markdown-output", default="reports/area-quality.md")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--min-score", type=int, default=75)
    args = parser.parse_args()

    environments = ["codex", "opencode", "claude", "gemini", "antigravity", "cursor"] if args.environment == "all" else [args.environment]
    scores = [assess_spec(spec, env) for spec in spec_dirs() for env in environments]

    json_path = ROOT / args.json_output
    md_path = ROOT / args.markdown_output
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps([asdict(score) for score in scores], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(markdown_report(scores), encoding="utf-8")

    print(f"Wrote {json_path.relative_to(ROOT)}")
    print(f"Wrote {md_path.relative_to(ROOT)}")

    failing = [score for score in scores if score.score < args.min_score]
    if args.strict and failing:
        for score in failing:
            print(f"{score.specialization} ({score.environment}) scored {score.score}, below {args.min_score}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
