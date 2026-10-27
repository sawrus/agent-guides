#!/usr/bin/env python3
"""Check rules, skills, and workflows against docs/artifact-standard.md.

Pack mode (default) checks `areas/**` of the knowledge base and every requirement marked `auto`. Project mode
(`--project <dir>`) checks the company rules of an installed project (`.agent/company/**`) and reports which pack
rules they duplicate (ART-K1, ART-K2).

A finding has an id (`ART-R3`), a path, and a message. Its baseline key is `<id> <path>`. The committed baseline
(`scripts/check_artifacts_baseline.json`) lists known findings; only findings outside it fail the run. Python 3.11+
standard library only.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from itertools import combinations
import json
import os
from pathlib import Path
import re
import sys
import tomllib

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.dont_write_bytecode = True  # keep scripts/ free of __pycache__ (make check-no-pycache)
sys.path.insert(0, str(SCRIPTS))
import context_budget  # noqa: E402  (shared token estimate and install-based budget)

DEFAULT_CONFIG = SCRIPTS / 'check_artifacts.toml'
DEFAULT_BASELINE = SCRIPTS / 'check_artifacts_baseline.json'
DENY_ENV = 'AGENTIC_DENY_TERMS_FILE'
FRONT = re.compile(r'\A---\n(.*?)\n---[ \t]*\n?', re.S)
FENCE = re.compile(r'^\s*(```|~~~)')
LIST_ITEM = re.compile(r'^\s*(?:[-*+]|\d+[.)])\s+(.*\S)')
HEADING = re.compile(r'^(#{1,6})\s+(.*)')
LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
STEP = re.compile(r'^(#{2,4})\s+(?:Step\s+)?(\d+)\s*[.):—-]')
WORD = re.compile(r"[a-z0-9_]+(?:['-][a-z0-9_]+)*")
KEBAB = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
STOPWORDS = frozenset(
    'a an the and or but if then else of to in on at by for with from as is are be been was were it its this that '
    'these those your you we our they their them do does done not no only all any each every one per via into '
    'than so such can may should will would must when where which who what how also before after same'.split())
TEXT_SUFFIXES = frozenset({'.md', '.txt', '.yml', '.yaml', '.json', '.toml', '.py', '.sh', '.js', '.ts', '.tf',
                           '.sql', '.cfg', '.ini', '.env', '.tmpl', ''})
KIND_IDS = {
    'rule': ('ART-C1', 'ART-C2', 'ART-C3', 'ART-C4', 'ART-C5', 'ART-C6', 'ART-C7',
             'ART-R1', 'ART-R2', 'ART-R3', 'ART-R4'),
    'skill': ('ART-C1', 'ART-C2', 'ART-C3', 'ART-C4', 'ART-C5', 'ART-C6', 'ART-C7',
              'ART-S1', 'ART-S3', 'ART-S4', 'ART-S5', 'ART-S6'),
    'workflow': ('ART-C1', 'ART-C2', 'ART-C3', 'ART-C4', 'ART-C5', 'ART-C6', 'ART-C7',
                 'ART-W1', 'ART-W2', 'ART-W4', 'ART-W6'),
    'company': ('ART-C1', 'ART-C2', 'ART-C3', 'ART-C4', 'ART-C7', 'ART-R1', 'ART-R2', 'ART-R3', 'ART-R4',
                'ART-K1', 'ART-K2'),
    'file': ('ART-C6',),
}


# --- parsing helpers ---------------------------------------------------------------------------------------

def scalar(value: str):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
        return value[1:-1]
    if value.startswith('[') and value.endswith(']'):
        return [scalar(v) for v in value[1:-1].split(',') if v.strip()]
    if value in ('true', 'false'):
        return value == 'true'
    return value


def parse_front(text: str) -> tuple[dict | None, str]:
    """YAML subset of artifact frontmatter: scalars, lists, block scalars, and one level of nested maps."""
    match = FRONT.match(text)
    if not match:
        return None, text
    data: dict = {}
    key = sub = block = None
    for raw in match.group(1).splitlines():
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        line = raw.strip()
        if not raw[0].isspace():
            sub = block = None
            name, _, value = line.partition(':')
            key, value = name.strip(), value.strip()
            if value in ('>', '|', '>-', '|-'):
                data[key], block = '', key
            else:
                data[key] = scalar(value) if value else None
            continue
        if key is None:
            continue
        if block:
            data[key] = f'{data[key]} {line}'.strip()
            continue
        container = data.get(key)
        if line.startswith('-'):
            item = scalar(line[1:])
            if isinstance(container, dict) and sub is not None:
                if not isinstance(container.get(sub), list):
                    container[sub] = []
                container[sub].append(item)
            else:
                if not isinstance(container, list):
                    data[key] = container = []
                container.append(item)
        else:
            name, _, value = line.partition(':')
            if not isinstance(container, dict):
                data[key] = container = {}
            sub = name.strip()
            container[sub] = scalar(value) if value.strip() else None
    return data, text[match.end():]


def as_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def strip_code(lines: list[str]) -> list[tuple[int, str]]:
    """(1-based line number, text) of lines outside fenced code blocks."""
    out, inside = [], False
    for number, line in enumerate(lines, 1):
        if FENCE.match(line):
            inside = not inside
            continue
        if not inside:
            out.append((number, line))
    return out


def code_blocks(lines: list[str]) -> list[int]:
    """Inner line count of each fenced code block."""
    blocks, inside, size = [], False, 0
    for line in lines:
        if FENCE.match(line):
            if inside:
                blocks.append(size)
            inside, size = not inside, 0
        elif inside:
            size += 1
    return blocks


def plain(text: str) -> str:
    return re.sub(r'[*_`>#|]', ' ', text)


def words(text: str) -> list[str]:
    return WORD.findall(plain(text).lower())


def content_words(text: str) -> set[str]:
    return {w for w in words(text) if w not in STOPWORDS and len(w) > 1}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def shingles(text: str, size: int) -> set[tuple[str, ...]]:
    tokens = words(text)
    return {tuple(tokens[i:i + size]) for i in range(len(tokens) - size + 1)}


def list_items(body: str) -> list[str]:
    return [m.group(1) for _, line in strip_code(body.splitlines()) if (m := LIST_ITEM.match(line))]


def statements(body: str) -> list[str]:
    """List items and prose sentences outside code blocks, headings, and tables."""
    out = []
    for _, line in strip_code(body.splitlines()):
        stripped = line.strip()
        if not stripped or HEADING.match(stripped) or stripped.startswith(('|', '<!--', '-->')):
            continue
        item = LIST_ITEM.match(line)
        text = item.group(1) if item else stripped
        out += [s for s in re.split(r'(?<=[.!?;])\s+', text) if s.strip()]
    return out


def line_count(text: str) -> int:
    return len(text.splitlines())


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding='utf-8')
    except (UnicodeDecodeError, OSError):
        return None


# --- model ------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Finding:
    id: str
    path: str
    message: str

    @property
    def key(self) -> str:
        return f'{self.id} {self.path}'


@dataclass
class Artifact:
    kind: str
    path: Path
    rel: str
    area: str
    spec: str
    text: str
    front: dict | None
    body: str
    install_name: str
    spec_dir: Path | None = None
    extra: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.path.parent.name if self.kind == 'skill' else self.path.stem


def load_artifact(kind: str, path: Path, base: Path, area: str, spec: str, spec_dir: Path | None) -> Artifact:
    text = path.read_text(encoding='utf-8')
    front, body = parse_front(text)
    bucket = {'rule': 'rules', 'company': 'company', 'skill': 'skills', 'workflow': 'workflows'}[kind]
    install = f'{bucket}/{path.parent.name if kind == "skill" else path.name}'
    return Artifact(kind, path, path.relative_to(base).as_posix(), area, spec, text, front, body, install, spec_dir)


def pack_specs(root: Path):
    areas = root / 'areas'
    if not areas.is_dir():
        return
    for area in sorted(p for p in areas.iterdir() if p.is_dir() and p.name != 'template'):
        for spec in sorted(p for p in area.iterdir() if p.is_dir()):
            yield area.name, spec.name, spec


def discover_pack(root: Path) -> list[Artifact]:
    found = []
    for area, spec, spec_dir in pack_specs(root):
        for path in sorted(spec_dir.glob('rules/*.md')):
            found.append(load_artifact('rule', path, root, area, spec, spec_dir))
        for path in sorted(spec_dir.glob('skills/*/SKILL.md')):
            found.append(load_artifact('skill', path, root, area, spec, spec_dir))
        for path in sorted(spec_dir.glob('workflows/*.md')):
            found.append(load_artifact('workflow', path, root, area, spec, spec_dir))
    return found


# --- configuration ----------------------------------------------------------------------------------------

def load_config(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding='utf-8'))


def deny_matchers(config: dict, terms_file: Path | None) -> list[tuple[str, re.Pattern]]:
    """(label, regex). Built-in patterns print themselves; external terms print only their index."""
    matchers = [(f'pattern {p!r}', re.compile(p)) for p in config['deny'].get('patterns', [])]
    if terms_file:
        lines = terms_file.read_text(encoding='utf-8').splitlines()
        for number, raw in enumerate(lines, 1):
            term = raw.strip()
            if not term or term.startswith('#'):
                continue
            regex = term[3:] if term.startswith('re:') else re.escape(term)
            matchers.append((f'external deny term #{number}', re.compile(regex, re.I)))
    return matchers


def core_statements(root: Path, config: dict) -> list[tuple[str, set[str]]]:
    path = root / config['common']['core_file']
    text = read_text(path) or ''
    wanted = {s.lower() for s in config['common']['core_sections']}
    keep, section = [], None
    for line in text.splitlines():
        heading = HEADING.match(line)
        if heading:
            section = heading.group(2).strip().lower() if len(heading.group(1)) == 2 else section
            continue
        if section in wanted:
            keep.append(line)
    # Join wrapped list items so one core statement is one unit.
    joined, current = [], ''
    for line in keep:
        if LIST_ITEM.match(line) or not line.strip():
            if current:
                joined.append(current)
            current = line.strip()
        else:
            current = f'{current} {line.strip()}'
    if current:
        joined.append(current)
    out = []
    for statement in statements('\n'.join(joined)):
        cw = content_words(statement)
        if len(cw) >= config['common']['core_min_words']:
            out.append((statement, cw))
    return out


# --- checks: all kinds ------------------------------------------------------------------------------------

def check_c1(a: Artifact, cfg: dict) -> list[Finding]:
    if a.front is None:
        return [Finding('ART-C1', a.rel, 'no YAML frontmatter')]
    description = a.front.get('description')
    if not isinstance(description, str) or not description.strip():
        return [Finding('ART-C1', a.rel, 'frontmatter has no `description`')]
    if a.kind == 'skill':  # ART-S1 sets the skill limit (1,024 chars, trigger words allowed)
        return []
    out = []
    limit = cfg['common']['description_max']
    if len(description) > limit:
        out.append(Finding('ART-C1', a.rel, f'description is {len(description)} chars (max {limit})'))
    if len(re.findall(r'[.!?](?:\s+[A-Z])', description)) >= 1:
        out.append(Finding('ART-C1', a.rel, 'description has more than one sentence'))
    return out


def check_c2(a: Artifact, cfg: dict, core: list[tuple[str, set[str]]]) -> list[Finding]:
    common = cfg['common']
    out = []
    for pattern in common.get('core_patterns', []):
        if re.search(pattern, a.body, re.I):
            out.append(Finding('ART-C2', a.rel, f'repeats a core AGENTS.md convention ({pattern!r})'))
    hits = []
    for statement in statements(a.body):
        cw = content_words(statement)
        if len(cw) < common['core_min_words']:
            continue
        best = max(((jaccard(cw, core_cw), text) for text, core_cw in core), default=(0.0, ''))
        if best[0] >= common['core_similarity']:
            hits.append((best[0], statement))
    if hits:
        score, statement = max(hits)
        out.append(Finding('ART-C2', a.rel, f'{len(hits)} statement(s) repeat the core AGENTS.md, e.g. '
                                             f'"{statement[:80]}" ({score:.2f})'))
    return out


def check_c3(items: list[Artifact], cfg: dict) -> list[Finding]:
    size, threshold = cfg['common']['shingle_size'], cfg['common']['duplicate_similarity']
    minimum = cfg['common']['duplicate_min_shingles']
    sets = [(a, shingles(a.body, size)) for a in items]
    sets = [(a, s) for a, s in sets if len(s) >= minimum]
    out = []
    for (a, sa), (b, sb) in combinations(sets, 2):
        score = jaccard(sa, sb)
        if score >= threshold:
            out.append(Finding('ART-C3', a.rel, f'near-duplicate of {b.rel} ({score:.2f} >= {threshold})'))
            out.append(Finding('ART-C3', b.rel, f'near-duplicate of {a.rel} ({score:.2f} >= {threshold})'))
    return out


def check_c4(a: Artifact, by_spec: dict) -> list[Finding]:
    out = []
    if a.front:
        own = by_spec.get((a.area, a.spec), {})
        for ref in as_list(a.front.get('related-rules')):
            name = Path(re.sub(r'\s*\(.*\)$', '', ref)).name
            name = name if name.endswith('.md') else f'{name}.md'
            if f'rules/{name}' not in own:
                where = sorted(f'{ar}/{sp}' for (ar, sp), names in by_spec.items() if f'rules/{name}' in names)
                hint = f' (only in {", ".join(where)})' if where else ''
                out.append(Finding('ART-C4', a.rel, f'related rule `{ref}` is not in the same install selection{hint}'))
        for ref in as_list(a.front.get('uses-skills')) + as_list(a.front.get('related-skills')):
            if f'skills/{ref}' not in own:
                out.append(Finding('ART-C4', a.rel, f'skill `{ref}` is not in the same install selection'))
    for _, line in strip_code(a.body.splitlines()):
        for target in LINK.findall(line):
            if re.match(r'^(?:[a-z][a-z0-9+.-]*:|#|<|\{)', target, re.I) or '{{' in target:
                continue
            resolved = (a.path.parent / target.split('#', 1)[0]).resolve()
            if not resolved.exists():
                out.append(Finding('ART-C4', a.rel, f'link `{target}` does not resolve'))
            elif a.spec_dir is not None and not resolved.is_relative_to(a.spec_dir.resolve()):
                out.append(Finding('ART-C4', a.rel, f'link `{target}` leaves the install selection'))
    return out


def check_c5(items: list[Artifact]) -> list[Finding]:
    """Specs of one area can be installed together; their files land in the same target directories."""
    owners: dict[tuple[str, str], list[Artifact]] = {}
    for a in items:
        owners.setdefault((a.area, a.install_name), []).append(a)
    out = []
    for (_, install), group in owners.items():
        if len({a.spec for a in group}) < 2:
            continue
        for a in group:
            others = ', '.join(b.rel for b in group if b is not a)
            out.append(Finding('ART-C5', a.rel, f'installs as `{install}` like {others}'))
    return out


def check_c6(rel: str, text: str, matchers, allow: list[str]) -> list[Finding]:
    out = []
    for number, line in enumerate(text.splitlines(), 1):
        for allowed in allow:
            line = re.sub(re.escape(allowed), ' ', line, flags=re.I)
        for label, regex in matchers:
            if regex.search(line):
                out.append(Finding('ART-C6', rel, f'line {number} matches {label}'))
    return out


def check_c7(a: Artifact, cfg: dict) -> list[Finding]:
    roles = cfg['roles']
    out = []
    handles = '|'.join(map(re.escape, roles['handles']))
    found = sorted(set(re.findall(rf'(?<![\w.@])@({handles})\b', a.body)))
    if found:
        out.append(Finding('ART-C7', a.rel, f'assigns roles: {", ".join("@" + h for h in found)}'))
    for pattern in roles['role_patterns']:
        if re.search(pattern, a.body, re.I):
            out.append(Finding('ART-C7', a.rel, f'asks for role subagents ({pattern!r})'))
    reports = sorted({m.group(0) for p in roles['report_patterns'] for m in re.finditer(p, a.text)})
    if reports:
        out.append(Finding('ART-C7', a.rel, f'requires report files: {", ".join(reports[:5])}'))
    return out


# --- checks: rules ----------------------------------------------------------------------------------------

def checkable(item: str, verbs: re.Pattern, objects: re.Pattern) -> bool:
    concrete = ('`' in item or re.search(r'\d|--\w|\w/\w|\.\w{2,5}\b|"[^"]+"', item) or objects.search(item))
    return bool(verbs.search(item) and concrete)


def check_rule(a: Artifact, cfg: dict) -> list[Finding]:
    rule = cfg['rule']
    out = []
    front = a.front or {}
    trigger = front.get('trigger')
    has_paths = bool(as_list(front.get('paths')))
    if trigger == 'always_on':
        if a.rel not in rule.get('always_on_allowed', []):
            out.append(Finding('ART-R1', a.rel, '`trigger: always_on` is reserved for rules that apply to every change'))
    elif trigger not in (None, 'manual'):
        out.append(Finding('ART-R1', a.rel, f'`trigger: {trigger}` is not used; scope the rule with `paths:`'))
    if not has_paths and trigger not in ('manual', 'always_on'):
        out.append(Finding('ART-R1', a.rel, 'needs `paths:` globs or `trigger: manual`'))
    for name in rule['forbidden_fields']:
        if name in front:
            out.append(Finding('ART-R1', a.rel, f'field `{name}` is not used'))

    verbs = re.compile(r'\b(?:' + '|'.join(map(re.escape, rule['verbs'])) + r')\b', re.I)
    objects = re.compile(r'\b(?:' + '|'.join(map(re.escape, rule['objects'])) + r')s?\b', re.I)
    items = list_items(a.body)
    if not items:
        out.append(Finding('ART-R2', a.rel, 'no list items: state the constraints as a list of imperatives'))
    else:
        good = sum(checkable(i, verbs, objects) for i in items)
        share = good / len(items)
        if share < rule['checkable_share_min']:
            out.append(Finding('ART-R2', a.rel, f'{good}/{len(items)} list items are checkable imperatives '
                                                f'({share:.0%} < {rule["checkable_share_min"]:.0%})'))

    lines, tokens = line_count(a.text), context_budget.tokens(a.text)
    if lines > rule['max_lines'] or tokens > rule['max_tokens']:
        out.append(Finding('ART-R3', a.rel, f'{lines} lines, {tokens} tokens (max {rule["max_lines"]} lines, '
                                            f'{rule["max_tokens"]} tokens)'))
    out += check_code(a, rule['code_block_max_lines'], rule['code_share_max'], 'ART-R4')
    return out


def check_code(a: Artifact, block_max: int | None, share_max: float, check_id: str) -> list[Finding]:
    lines = a.text.splitlines()
    blocks = code_blocks(lines)
    out = []
    if block_max is not None:
        long = [n for n in blocks if n > block_max]
        if long:
            out.append(Finding(check_id, a.rel, f'{len(long)} code block(s) over {block_max} lines (longest {max(long)})'))
    share = sum(n + 2 for n in blocks) / max(1, len(lines))
    if share > share_max:
        out.append(Finding(check_id, a.rel, f'code blocks are {share:.0%} of the file (max {share_max:.0%})'))
    return out


# --- checks: skills ---------------------------------------------------------------------------------------

def check_skill(a: Artifact, cfg: dict, referenced: set, matchers_s5: list[re.Pattern]) -> list[Finding]:
    skill = cfg['skill']
    out = []
    front = a.front or {}
    description = front.get('description')
    if isinstance(description, str) and len(description) > skill['description_max']:
        out.append(Finding('ART-S1', a.rel, f'description is {len(description)} chars (max {skill["description_max"]})'))
    name = front.get('name')
    if name != a.name:
        out.append(Finding('ART-S1', a.rel, f'`name: {name}` must equal the directory name `{a.name}`'))
    elif not KEBAB.match(a.name):
        out.append(Finding('ART-S1', a.rel, f'`{a.name}` is not kebab-case'))

    lines = line_count(a.text)
    if lines > skill['max_lines']:
        out.append(Finding('ART-S3', a.rel, f'SKILL.md has {lines} lines (max {skill["max_lines"]})'))
    extra_files = [p for p in sorted(a.path.parent.rglob('*')) if p.is_file() and p != a.path]
    extra_lines = sum(line_count(t) for p in extra_files if (t := read_text(p)) is not None)
    if extra_lines > skill['references_max_lines']:
        out.append(Finding('ART-S3', a.rel, f'references and assets have {extra_lines} lines in '
                                            f'{len(extra_files)} files (max {skill["references_max_lines"]})'))
    out += check_code(a, None, skill['code_share_max'], 'ART-S4')

    for path in [a.path, *extra_files]:
        text = read_text(path)
        if text is None:
            continue
        hits = sorted({m.group(0).strip() for r in matchers_s5 for m in r.finditer(text)})
        if hits:
            where = path.relative_to(a.path.parent).as_posix()
            out.append(Finding('ART-S5', a.rel, f'framework scaffolding in {where}: {", ".join(hits[:4])}'))

    trigger = re.compile(skill['trigger_pattern'], re.I)
    if (a.area, a.spec, a.name) not in referenced and not trigger.search(str(description or '')):
        out.append(Finding('ART-S6', a.rel, 'orphan: no workflow or rule links it and the description states '
                                            'no trigger ("Use when ...")'))
    return out


def skill_references(items: list[Artifact]) -> set[tuple[str, str, str]]:
    skills = {(a.area, a.spec, a.name) for a in items if a.kind == 'skill'}
    out = set()
    for a in items:
        if a.kind not in ('rule', 'workflow'):
            continue
        front = a.front or {}
        for name in as_list(front.get('uses-skills')) + as_list(front.get('related-skills')):
            out.add((a.area, a.spec, name))
        for area, spec, name in skills:
            if (area, spec) == (a.area, a.spec) and re.search(rf'skills/{re.escape(name)}\b|`{re.escape(name)}`', a.body):
                out.add((area, spec, name))
    return out


# --- checks: workflows ------------------------------------------------------------------------------------

def workflow_steps(body: str) -> list[tuple[str, str]]:
    """(step number, step text) for numbered step headings outside code blocks."""
    lines = body.splitlines()
    kept = strip_code(lines)
    marks = [(i, m.group(2), len(m.group(1))) for i, (_, line) in enumerate(kept) if (m := STEP.match(line))]
    steps = []
    for k, (index, number, level) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(kept)
        for j in range(index + 1, end):
            heading = HEADING.match(kept[j][1])
            if heading and len(heading.group(1)) <= level:
                end = j
                break
        steps.append((number, '\n'.join(line for _, line in kept[index:end])))
    return steps


def check_workflow(a: Artifact, cfg: dict) -> list[Finding]:
    wf = cfg['workflow']
    out = []
    front = a.front or {}
    missing = [k for k in wf['required_fields'] if k not in front]
    if missing:
        out.append(Finding('ART-W1', a.rel, f'frontmatter misses {", ".join(missing)}'))
    if 'type' in front and front.get('type') != 'workflow':
        out.append(Finding('ART-W1', a.rel, '`type` must be `workflow`'))
    name = front.get('name')
    if name and front.get('trigger') and front.get('trigger') != f'/{name}':
        out.append(Finding('ART-W1', a.rel, f'`trigger` must be `/{name}`'))
    selection = front.get('selection')
    if not isinstance(selection, dict) or not str(selection.get('use-when') or '').strip():
        out.append(Finding('ART-W1', a.rel, 'frontmatter misses `selection.use-when`'))
    forbidden = [k for k in wf['forbidden_fields'] if k in front]
    if isinstance(front.get('execution'), dict) and 'initiator' in front['execution']:
        forbidden.append('execution.initiator')
    if forbidden:
        out.append(Finding('ART-W1', a.rel, f'fields not used: {", ".join(forbidden)}'))

    steps = workflow_steps(a.body)
    if not wf['min_steps'] <= len(steps) <= wf['max_steps']:
        out.append(Finding('ART-W2', a.rel, f'{len(steps)} steps (need {wf["min_steps"]}–{wf["max_steps"]})'))
    no_do = [n for n, text in steps if not re.search(r'\*\*Do\b', text)]
    no_done = [n for n, text in steps if not re.search(r'\*\*Done when\b', text, re.I)]
    if no_do:
        out.append(Finding('ART-W2', a.rel, f'steps without **Do**: {", ".join(no_do)}'))
    if no_done:
        out.append(Finding('ART-W2', a.rel, f'steps without **Done when**: {", ".join(no_done)}'))

    lines, tokens = line_count(a.text), context_budget.tokens(a.text)
    if lines > wf['max_lines'] or tokens > wf['max_tokens']:
        out.append(Finding('ART-W4', a.rel, f'{lines} lines, {tokens} tokens (max {wf["max_lines"]} lines, '
                                            f'{wf["max_tokens"]} tokens)'))

    production, ask = re.compile(wf['production_pattern'], re.I), re.compile(wf['ask_pattern'], re.I)
    units = steps or [('body', a.body)]
    risky = [n for n, text in units if production.search(text) and not ask.search(text)]
    if risky:
        out.append(Finding('ART-W6', a.rel, f'step(s) {", ".join(risky)} touch production without "ask the user first"'))
    return out


# --- budget -----------------------------------------------------------------------------------------------

def check_budget(root: Path, cfg: dict, binary: Path) -> tuple[list[Finding], list[str]]:
    budget = cfg['budget']
    if not binary.is_file():
        return [], [f'ART-B1 skipped: {binary} not found (run `make build`)']
    selections = [*context_budget.installable_specs(root), *budget.get('common_selections', [])]
    out, notes = [], []
    for specs in selections:
        try:
            results = context_budget.measure_selection(binary, budget['hosts'], specs)
        except RuntimeError as exc:
            notes.append(str(exc))
            continue
        over = [f'{host} {parts["total"]}' for host, parts in results.items() if parts['total'] > budget['max_tokens']]
        if over:
            out.append(Finding('ART-B1', f'selection:{specs}', f'always-on tokens over {budget["max_tokens"]}: '
                                                               f'{", ".join(over)}'))
    return out, notes


# --- runs -------------------------------------------------------------------------------------------------

def run_pack(root: Path, cfg: dict, matchers, budget_binary: Path | None) -> tuple[list[Finding], dict, list[str]]:
    items = discover_pack(root)
    core = core_statements(root, cfg)
    by_spec: dict[tuple[str, str], set[str]] = {}
    for a in items:
        by_spec.setdefault((a.area, a.spec), set()).add(a.install_name)
    referenced = skill_references(items)
    s5 = [re.compile(p, re.I) for p in cfg['skill']['scaffolding']]
    findings: list[Finding] = []
    kinds = {a.rel: a.kind for a in items}
    for a in items:
        findings += check_c1(a, cfg) + check_c2(a, cfg, core) + check_c4(a, by_spec) + check_c7(a, cfg)
        if a.kind == 'rule':
            findings += check_rule(a, cfg)
        elif a.kind == 'skill':
            findings += check_skill(a, cfg, referenced, s5)
        else:
            findings += check_workflow(a, cfg)
    findings += check_c3(items, cfg) + check_c5(items)
    allow = cfg['deny'].get('allow', [])
    for path in sorted((root / 'areas').rglob('*')):
        if path.is_file() and path.suffix in TEXT_SUFFIXES and (text := read_text(path)) is not None:
            rel = path.relative_to(root).as_posix()
            kinds.setdefault(rel, 'file')
            findings += check_c6(rel, text, matchers, allow)
    notes: list[str] = []
    if budget_binary is not None:
        extra, notes = check_budget(root, cfg, budget_binary)
        findings += extra
    return findings, kinds, notes


def pack_rule_index(kb: Path) -> dict[str, list[str]]:
    """Rule file name -> `area/spec/rule` ids in the knowledge base."""
    index: dict[str, list[str]] = {}
    for area, spec, spec_dir in pack_specs(kb):
        for path in sorted(spec_dir.glob('rules/*.md')):
            index.setdefault(path.name, []).append(f'{area}/{spec}/{path.stem}')
    return index


def run_project(project: Path, kb: Path, cfg: dict) -> tuple[list[Finding], dict, dict]:
    company_dir = project / '.agent/company'
    company = [load_artifact('company', p, project, 'company', 'company', None)
               for p in sorted(company_dir.rglob('*.md'))] if company_dir.is_dir() else []
    pack = [load_artifact('rule', p, project, 'pack', 'pack', None)
            for p in sorted((project / '.agent/rules').glob('*.md'))]
    core = core_statements(kb, cfg)
    index = pack_rule_index(kb)
    comp = cfg['company']
    size = cfg['common']['shingle_size']
    findings: list[Finding] = []
    suggestions: list[dict] = []
    for a in company:
        findings += check_c1(a, cfg) + check_c2(a, cfg, core) + check_c4(a, {}) + check_c7(a, cfg) + check_rule(a, cfg)
        replaces = as_list((a.front or {}).get('replaces'))
        replaced_names = set()
        for ref in replaces:
            name = f'{Path(ref).name.removesuffix(".md")}.md'
            replaced_names.add(name)
            if ref.removesuffix('.md') not in index.get(name, []):
                findings.append(Finding('ART-K1', a.rel, f'`replaces: {ref}` names no pack rule'))
            if (project / '.agent/rules' / name).is_file():
                findings.append(Finding('ART-K1', a.rel, f'replaced pack rule `{ref}` is still installed: add it to '
                                                         '`company_rules.exclude`'))
        a_sh = shingles(a.body, size)
        a_st = [cw for s in statements(a.body) if len(cw := content_words(s)) >= cfg['common']['core_min_words']]
        for p in pack:
            if p.path.name in replaced_names:
                continue
            p_st = [cw for s in statements(p.body) if len(cw := content_words(s)) >= cfg['common']['core_min_words']]
            restated = sum(any(jaccard(x, y) >= comp['statement_similarity'] for y in p_st) for x in a_st)
            topic = jaccard(a_sh, shingles(p.body, size))
            pack_ids = index.get(p.path.name, [p.path.stem])
            if topic >= comp['topic_similarity'] or (a_st and restated / len(a_st) >= comp['topic_statement_share']):
                findings.append(Finding('ART-K1', a.rel, f'covers the topic of pack rule {p.rel}: add `replaces: '
                                                         f'[{pack_ids[0]}]` and exclude it'))
                suggestions.append({'company': a.rel, 'pack': p.rel, 'replaces': pack_ids})
            elif restated:
                findings.append(Finding('ART-K2', a.rel, f'{restated} statement(s) restate pack rule {p.rel}'))
    findings += check_c3(company, cfg)
    kinds = {a.rel: 'company' for a in company}
    return findings, kinds, {'replace_suggestions': suggestions}


# --- report -----------------------------------------------------------------------------------------------

def load_baseline(path: Path | None) -> set[str]:
    if path is None or not path.is_file():
        return set()
    return set(json.loads(path.read_text(encoding='utf-8')).get('findings', []))


def write_baseline(path: Path, findings: list[Finding]) -> None:
    data = {'comment': 'Known findings of scripts/check_artifacts.py (`<id> <path>`). Only shrink this list; '
                       'regenerate with `make check-artifacts ARTIFACTS_ARGS=--write-baseline`.',
            'findings': sorted({f.key for f in findings})}
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def scores(findings: list[Finding], kinds: dict[str, str]) -> dict[str, int]:
    failed: dict[str, set[str]] = {}
    for f in findings:
        failed.setdefault(f.path, set()).add(f.id)
    out = {}
    for path, kind in kinds.items():
        applicable = KIND_IDS[kind]
        bad = len(failed.get(path, set()) & set(applicable))
        out[path] = round(100 * (1 - bad / len(applicable)))
    return out


def counts_by_id(findings: list[Finding]) -> dict[str, int]:
    out: dict[str, set[str]] = {}
    for f in findings:
        out.setdefault(f.id, set()).add(f.path)
    return {k: len(v) for k, v in sorted(out.items(), key=lambda kv: (kv[0][:5], int(re.sub(r'\D', '', kv[0]) or 0)))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', type=Path, default=ROOT, help='Knowledge base root (holds areas/ and AGENTS.md)')
    parser.add_argument('--project', type=Path, help='Check an installed project: .agent/company vs .agent/rules')
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--baseline', type=Path, help=f'Default: {DEFAULT_BASELINE.relative_to(ROOT)} in pack mode')
    parser.add_argument('--no-baseline', action='store_true', help='Fail on every finding')
    parser.add_argument('--write-baseline', action='store_true', help='Write all current findings to the baseline')
    parser.add_argument('--strict-baseline', action='store_true', help='Fail on stale baseline entries')
    parser.add_argument('--deny-terms-file', type=Path, default=os.environ.get(DENY_ENV) or None,
                        help=f'Extra ART-C6 terms, one per line (default: ${DENY_ENV})')
    parser.add_argument('--binary', type=Path, default=ROOT / 'target/debug/agentic', help='agentic binary for ART-B1')
    parser.add_argument('--no-budget', action='store_true', help='Skip ART-B1 (needs the agentic binary)')
    parser.add_argument('--json', action='store_true', help='Print a JSON report instead of text')
    parser.add_argument('--verbose', action='store_true', help='Print baselined findings and all file scores')
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    root = args.root.resolve()
    extra: dict = {}
    if args.project:
        findings, kinds, extra = run_project(args.project.resolve(), root, cfg)
        notes: list[str] = []
        baseline_path = args.baseline
    else:
        matchers = deny_matchers(cfg, args.deny_terms_file)
        findings, kinds, notes = run_pack(root, cfg, matchers, None if args.no_budget else args.binary)
        baseline_path = args.baseline or (DEFAULT_BASELINE if root == ROOT else None)
    findings = sorted(set(findings), key=lambda f: (f.path, f.id, f.message))

    if args.write_baseline:
        if baseline_path is None:
            parser.error('--write-baseline needs --baseline outside the repository root')
        write_baseline(baseline_path, findings)
        print(f'[check-artifacts] wrote {len({f.key for f in findings})} keys to {baseline_path}')
        return 0

    baseline = set() if args.no_baseline else load_baseline(baseline_path)
    keys = {f.key for f in findings}
    new = [f for f in findings if f.key not in baseline]
    stale = sorted(baseline - keys)
    file_scores = scores(findings, kinds)
    fail = bool(new) or (args.strict_baseline and bool(stale))

    if args.json:
        print(json.dumps({'findings': [f.__dict__ | {'baselined': f.key in baseline} for f in findings],
                          'new': [f.key for f in new], 'stale_baseline': stale, 'counts': counts_by_id(findings),
                          'scores': file_scores, 'notes': notes, **extra}, indent=2))
        return 1 if fail else 0

    shown = findings if args.verbose else new
    current = None
    for f in shown:
        if f.path != current:
            current = f.path
            score = file_scores.get(f.path)
            print(f'{f.path}' + (f'  score {score}' if score is not None else ''))
        mark = '' if f.key not in baseline else ' (baseline)'
        print(f'  {f.id}  {f.message}{mark}')
    if args.verbose:
        print('\nFile scores:')
        for path, score in sorted(file_scores.items(), key=lambda kv: (kv[1], kv[0])):
            print(f'  {score:>3}  {path}')
    for note in notes:
        print(f'[check-artifacts][warn] {note}')
    for key in stale:
        print(f'[check-artifacts][{"error" if args.strict_baseline else "warn"}] stale baseline: {key} '
              '(fixed; remove it from the baseline)')
    counts = counts_by_id(findings)
    new_counts = counts_by_id(new)
    print('\nFiles with findings by id (all / new):')
    for check_id, count in counts.items():
        print(f'  {check_id:<7} {count:>4} / {new_counts.get(check_id, 0)}')
    low = [s for s in file_scores.values() if s < 100]
    print(f'\n[check-artifacts] {len(kinds)} files, {len(low)} with findings, {len(keys)} finding keys, '
          f'{len({f.key for f in new})} new, {len(stale)} stale baseline')
    if fail:
        print('[check-artifacts][error] fix the new findings above (docs/artifact-standard.md)')
    return 1 if fail else 0


if __name__ == '__main__':
    raise SystemExit(main())
