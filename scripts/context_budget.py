#!/usr/bin/env python3
"""Offline always-on context budget per host (docs/agentic-v2-lean/README.md, criterion K1).

Installs the pack into throwaway projects and sums the text each host puts into context before the first
prompt: instruction files and their imports, unscoped rules, the main agent prompt, and the one-line
descriptions of skills, agents, and commands. Tokens are estimated as UTF-8 bytes / 4; the estimate is
for before/after comparison, not billing.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
HOSTS = ('claude', 'codex', 'opencode')
SELECTION = ('software', 'software.backend,software.general')  # default; --all-selections measures ART-B1
FRONT_MATTER = re.compile(r'\A---\n(.*?)\n---\n?', re.S)
# A loading directive in AGENTS.md that tells the agent to read every rule up front.
RULES_DIRECTIVE = re.compile(r'`\.agent/rules/\*\.md`')


def tokens(text):
    return (len(text.encode('utf-8')) + 3) // 4


def split_front_matter(text):
    match = FRONT_MATTER.match(text)
    return (match.group(1), text[match.end():]) if match else ('', text)


def field(meta, name):
    match = re.search(rf'^{name}:\s*(.+)$', meta, re.M)
    return match.group(1).strip().strip('"') if match else ''


def scoped(meta):
    """Rules with `paths:` load only when a matching file is touched (Claude Code path-scoped rules)."""
    return re.search(r'^paths:', meta, re.M) is not None


def read(path):
    return path.read_text(encoding='utf-8') if path.is_file() else ''


def expand_imports(path, seen=None):
    """CLAUDE.md `@path` lines pull whole files into context."""
    seen = seen if seen is not None else set()
    if path in seen or not path.is_file():
        return ''
    seen.add(path)
    text = read(path)
    for line in re.findall(r'^@(\S+)$', text, re.M):
        text += expand_imports((path.parent / line).resolve(), seen)
    return text


def unscoped_rules(folder):
    return [p for p in sorted(folder.glob('*.md')) if not scoped(split_front_matter(read(p))[0])]


def descriptions(paths):
    """Harnesses list name + description of every skill, agent, and command; bodies load on demand."""
    total = ''
    for path in paths:
        if path.suffix == '.toml':
            data = tomllib.loads(read(path))
            name, description = data.get('name', path.stem), data.get('description', '')
        else:
            meta, _ = split_front_matter(read(path))
            name, description = field(meta, 'name') or path.stem, field(meta, 'description')
        total += f'{name}: {description}\n'
    return total


def agent_body(path):
    return split_front_matter(read(path))[1]


def measure(host, project):
    parts = {}
    if host == 'claude':
        parts['instructions'] = expand_imports((project / '.claude/CLAUDE.md').resolve()) + expand_imports(
            (project / 'CLAUDE.md').resolve())
        parts['rules'] = ''.join(read(p) for p in unscoped_rules(project / '.claude/rules'))
        settings = json.loads(read(project / '.claude/settings.json') or '{}')
        main = settings.get('agent')
        parts['main_agent'] = agent_body(project / f'.claude/agents/{main}.md') if main else ''
        listed = [*(project / '.claude/skills').glob('*/SKILL.md'), *(project / '.claude/agents').glob('*.md'),
                  *(project / '.claude/commands').glob('*.md')]
    else:
        agents_md = read(project / 'AGENTS.md')
        parts['instructions'] = agents_md
        rule_dirs = [project / '.agent/rules'] if RULES_DIRECTIVE.search(agents_md) else []
        if host == 'opencode':
            config = json.loads(read(project / '.opencode/opencode.json') or '{}')
            for pattern in config.get('instructions', []):
                parts['instructions'] += ''.join(read(p) for p in sorted(project.glob(pattern)))
            primary = next((name for name, agent in config.get('agent', {}).items() if agent.get('mode') == 'primary'), None)
            parts['main_agent'] = agent_body(project / f'.opencode/agents/{primary}.md') if primary else ''
            skill_dirs = ('.opencode/skills', '.claude/skills', '.agents/skills')
            listed = [*(project / '.opencode/agents').glob('*.md'), *(project / '.opencode/commands').glob('*.md')]
        else:
            skill_dirs = ('.agents/skills',)
            listed = [*(project / '.codex/agents').glob('*.toml')]
        parts['rules'] = ''.join(read(p) for d in rule_dirs for p in unscoped_rules(d))
        listed += [p for d in skill_dirs for p in (project / d).glob('*/SKILL.md')]
    parts['descriptions'] = descriptions(listed)
    return {name: tokens(text) for name, text in parts.items()}


def install(binary, host, project, areas, specs):
    subprocess.run(['git', '-C', str(project), 'init', '-q'], check=True)
    result = subprocess.run([str(binary), 'install', '--project-dir', str(project), '--agent-os', host, '--areas', areas,
                             '--specializations', specs, '--no-doctor'], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f'[context-budget] install failed for {host} ({specs}): {result.stderr[-400:]}')


def installable_specs(root=ROOT):
    """Every `area.spec` that `agentic install` accepts and that ships at least one install bucket."""
    buckets = ('rules', 'skills', 'workflows')
    return [f'{area.name}.{spec.name}' for area in sorted((root / 'areas').iterdir())
            if area.is_dir() and area.name != 'template'
            for spec in sorted(area.iterdir()) if spec.is_dir() and any((spec / b).is_dir() for b in buckets)]


def common_selections(config=ROOT / 'scripts/check_artifacts.toml'):
    """Multi-spec selections that ART-B1 measures besides each single spec."""
    return list(tomllib.loads(read(config)).get('budget', {}).get('common_selections', []))


def all_selections(root=ROOT):
    return [*installable_specs(root), *common_selections()]


def measure_selection(binary, hosts, specs, areas=None):
    """Install `specs` (comma list of area.spec) once per host; return {host: {part: tokens, 'total': n}}."""
    areas = areas or ','.join(dict.fromkeys(s.split('.', 1)[0] for s in specs.split(',')))
    results = {}
    with tempfile.TemporaryDirectory(prefix='agentic-budget-') as tmp:
        for host in hosts:
            project = Path(tmp) / host
            project.mkdir()
            install(binary, host, project, areas, specs)
            results[host] = measure(host, project)
            results[host]['total'] = sum(results[host].values())
    return results


def print_table(results, title=None):
    columns = ('instructions', 'rules', 'main_agent', 'descriptions', 'total')
    if title:
        print(title)
    print('host      ' + ''.join(f'{c:>14}' for c in columns))
    for host, parts in results.items():
        print(f'{host:<10}' + ''.join(f'{parts.get(c, 0):>14}' for c in columns))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, default=ROOT / 'target/debug/agentic')
    parser.add_argument('--hosts', default=','.join(HOSTS))
    parser.add_argument('--areas', default=None, help='Default: the areas named in --specializations')
    parser.add_argument('--specializations', default=SELECTION[1])
    parser.add_argument('--all-selections', action='store_true',
                        help='Measure every installable spec and the common selections of check_artifacts.toml')
    parser.add_argument('--max-tokens', type=int, help='Fail when any host exceeds this always-on estimate')
    parser.add_argument('--json', type=Path, help='Also write the measurements as JSON')
    args = parser.parse_args()

    hosts = args.hosts.split(',')
    selections = all_selections() if args.all_selections else [args.specializations]
    report, over = {}, []
    try:
        for specs in selections:
            results = measure_selection(args.binary, hosts, specs, None if args.all_selections else args.areas)
            report[specs] = results
            print_table(results, f'selection {specs}' if args.all_selections else None)
            over += [f'{specs}:{h}' for h, parts in results.items()
                     if args.max_tokens and parts['total'] > args.max_tokens]
    except RuntimeError as exc:
        sys.exit(str(exc))
    if args.json:
        data = report if args.all_selections else report[selections[0]]
        args.json.write_text(json.dumps(data, indent=2) + '\n')
    if over:
        sys.exit(f'[context-budget] over {args.max_tokens} tokens: {", ".join(over)}')


if __name__ == '__main__':
    main()
