#!/usr/bin/env python3
"""Docs coverage of a change (docs/regulation.md section 3: DOC-3, DOC-4, DOC-5, DOC-6).

A change is the diff from the merge base of `--base` to `--head`. Every changed code path must match a
`covers:` glob of a docs page that changed in the same diff (DOC-4). Code paths are all tracked files except
the docs directory, tests, CI config, and the `exclude` globs of the config. A file is exempt when every commit
in the range that touches it carries the trailer `Docs-Not-Needed: <reason>` (DOC-5).

`--report-uncovered` lists tracked code that no docs page covers at all (DOC-6). The script is generic: point
`--config` at a project's own TOML file to use it in a target project. Python 3.11+ standard library only.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / 'scripts/check_docs_coverage.toml'
FRONT = re.compile(r'\A---\n(.*?)\n---[ \t]*(?:\n|\Z)', re.S)
DEFAULTS = {
    'docs_dir': 'docs',
    'trailer': 'Docs-Not-Needed',
    # Tests and CI config are never code for this check (DOC-4).
    'tests': ['tests/**', 'test/**', '**/tests/**', '**/test_*.py', '**/*_test.py', '**/*_test.go',
              '**/*.test.*', '**/*.spec.*', '**/src/test/**'],
    'ci': ['.github/**', '.gitlab-ci.yml', '.gitlab/**', '.circleci/**', 'Jenkinsfile', '.travis.yml',
           'azure-pipelines.yml', '.buildkite/**'],
    'exclude': [],
    # Manifests whose change is only the version line (the release policy bumps it in every PR) are not code.
    'version_files': [],
}
VERSION_LINE = re.compile(r'^\s*"?version"?\s*[=:]')
BROAD = {'**', '**/*', '*', '/**', './**'}


@dataclass(frozen=True)
class Violation:
    id: str
    path: str
    message: str

    def __str__(self) -> str:
        return f'{self.id}  {self.path}: {self.message}'


@lru_cache(maxsize=None)
def glob_regex(pattern: str) -> re.Pattern:
    """Gitignore-like glob anchored at the repository root: `*` stays in one segment, `**` crosses them."""
    pattern = pattern.strip().removeprefix('./').lstrip('/')
    if pattern.endswith('/'):
        pattern += '**'
    out, i = '', 0
    while i < len(pattern):
        if pattern.startswith('**/', i):
            out, i = out + '(?:.*/)?', i + 3
        elif pattern.startswith('**', i):
            out, i = out + '.*', i + 2
        elif pattern[i] == '*':
            out, i = out + '[^/]*', i + 1
        elif pattern[i] == '?':
            out, i = out + '[^/]', i + 1
        elif pattern[i] == '[':
            end = pattern.find(']', i + 1)
            if end == -1:
                out, i = out + re.escape('['), i + 1
            else:
                out, i = out + pattern[i:end + 1], end + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(rf'\A{out}\Z')


def matches(path: str, globs) -> bool:
    return any(glob_regex(g).match(path) for g in globs)


def parse_covers(text: str) -> list[str] | None:
    """`covers:` of a page's frontmatter; None when the key is absent."""
    match = FRONT.match(text)
    if not match:
        return None
    lines = match.group(1).splitlines()
    for index, line in enumerate(lines):
        key = re.match(r'^covers:\s*(.*)$', line)
        if not key:
            continue
        value = key.group(1).strip()
        if value.startswith('['):
            return [v.strip().strip('\'"') for v in value.strip('[]').split(',') if v.strip()]
        if value:
            return [value.strip('\'"')]
        globs = []
        for item in lines[index + 1:]:
            entry = re.match(r'^\s+-\s*(.+?)\s*$', item)
            if entry:
                globs.append(entry.group(1).strip('\'"'))
            elif item.strip() and not item.startswith((' ', '\t')):
                break
        return globs
    return None


def load_config(path: Path | None) -> dict:
    config = {k: list(v) if isinstance(v, list) else v for k, v in DEFAULTS.items()}
    if path and path.is_file():
        data = tomllib.loads(path.read_text(encoding='utf-8'))
        for key, value in data.items():
            config[key] = value
    return config


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f'git {" ".join(args)}: {result.stderr.strip()}')
    return result.stdout


def is_code(path: str, config: dict) -> bool:
    docs = config['docs_dir'].rstrip('/') + '/**'
    return not matches(path, [docs, *config['tests'], *config['ci'], *config['exclude']])


def page_kind(path: str, docs_dir: str) -> str | None:
    """Pages that need `covers:` (DOC-3): root design pages, feature READMEs, and incident pages."""
    rel = path[len(docs_dir) + 1:] if path.startswith(docs_dir + '/') else None
    if rel is None or not rel.endswith('.md'):
        return None
    parts = rel.split('/')
    if len(parts) == 1:
        return 'root'
    if parts[0] == 'incidents' and len(parts) == 2:
        return 'incident'
    if len(parts) == 2 and parts[1] == 'README.md':
        return 'feature'
    return None


def pages_at(repo: Path, ref: str, docs_dir: str) -> dict[str, list[str] | None]:
    """Docs pages at `ref` with their `covers:` (None when absent)."""
    names = git(repo, 'ls-tree', '-r', '--name-only', ref, '--', docs_dir).splitlines()
    out = {}
    for name in names:
        if name.endswith('.md'):
            out[name] = parse_covers(git(repo, 'show', f'{ref}:{name}'))
    return out


def exempt_files(repo: Path, base: str, head: str, trailer: str) -> set[str]:
    """Files whose every touching commit in base..head carries a non-empty `trailer`."""
    touched: dict[str, list[bool]] = {}
    for sha in git(repo, 'rev-list', '--no-merges', f'{base}..{head}').split():
        values = git(repo, 'log', '-1', f'--format=%(trailers:key={trailer},valueonly)', sha)
        has = bool(values.strip())
        files = git(repo, 'diff-tree', '--no-commit-id', '--name-only', '-r', '--no-renames', '--root', sha)
        for name in files.splitlines():
            touched.setdefault(name, []).append(has)
    return {name for name, flags in touched.items() if flags and all(flags)}


def version_only(repo: Path, base: str, head: str, paths: list[str]) -> set[str]:
    """Paths among `paths` whose diff from base to head changes only `version` lines."""
    out = set()
    for path in paths:
        diff = git(repo, 'diff', '-U0', base, head, '--', path).splitlines()
        lines = [l[1:] for l in diff if l[:1] in '+-' and not l.startswith(('+++', '---'))]
        if lines and all(VERSION_LINE.match(l) for l in lines):
            out.add(path)
    return out


def check_change(repo: Path, base: str, head: str, config: dict) -> list[Violation]:
    docs_dir = config['docs_dir'].rstrip('/')
    merge_base = git(repo, 'merge-base', base, head).strip()
    changed = git(repo, 'diff', '--name-only', '--no-renames', merge_base, head).splitlines()
    pages = pages_at(repo, head, docs_dir)
    changed_pages = {p: pages[p] for p in changed if p in pages}
    violations = []
    for page, covers in sorted(changed_pages.items()):
        kind = page_kind(page, docs_dir)
        if kind and covers is None:
            violations.append(Violation('DOC-3', page, f'{kind} page has no `covers:` frontmatter'))
        broad = sorted(g for g in covers or [] if g.strip() in BROAD)
        if broad:
            violations.append(Violation('DOC-6', page, f'`covers:` glob {broad[0]!r} covers everything; '
                                                       'add a root design page instead'))
    covering = [g for covers in changed_pages.values() for g in covers or [] if g.strip() not in BROAD]
    # A changed page also covers what it covered at the base, so a deleted file whose glob the page dropped counts.
    base_pages = pages_at(repo, merge_base, docs_dir)
    covering += [g for p in changed if p in base_pages for g in base_pages[p] or [] if g.strip() not in BROAD]
    exempt = exempt_files(repo, merge_base, head, config['trailer'])
    exempt |= version_only(repo, merge_base, head, [p for p in changed if matches(p, config['version_files'])])
    for path in changed:
        if not is_code(path, config) or matches(path, covering) or path in exempt:
            continue
        owners = sorted(p for p, covers in pages.items() if covers and matches(path, covers))
        hint = (f'update {", ".join(owners[:3])}' if owners
                else 'no docs page covers it; add a root design page (DOC-6)')
        violations.append(Violation('DOC-4', path, f'changed without a docs page change: {hint}, or add the '
                                                   f'trailer `{config["trailer"]}: <reason>`'))
    return violations


def report_uncovered(repo: Path, config: dict) -> tuple[list[str], list[str], list[str]]:
    """(uncovered code, pages without `covers:`, globs that match no tracked file) in the working tree."""
    docs_dir = config['docs_dir'].rstrip('/')
    tracked = [p for p in git(repo, 'ls-files').splitlines() if (repo / p).is_file()]
    pages = {p: parse_covers((repo / p).read_text(encoding='utf-8'))
             for p in tracked if p.startswith(docs_dir + '/') and p.endswith('.md')}
    globs = sorted({g for covers in pages.values() for g in covers or []})
    code = [p for p in tracked if is_code(p, config)]
    uncovered = [p for p in code if not matches(p, globs)]
    missing = sorted(p for p, covers in pages.items() if covers is None and page_kind(p, docs_dir))
    dead = [g for g in globs if not any(glob_regex(g).match(p) for p in tracked)]
    return uncovered, missing, dead


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--repo', type=Path, default=Path.cwd(), help='Repository root (default: current dir)')
    parser.add_argument('--base', default='origin/main', help='Base ref of the change (default: origin/main)')
    parser.add_argument('--head', default='HEAD')
    parser.add_argument('--config', type=Path, help=f'TOML config (default: {DEFAULT_CONFIG.relative_to(ROOT)} '
                                                    'in agent-guides, built-in defaults elsewhere)')
    parser.add_argument('--report-uncovered', action='store_true', help='List code that no docs page covers')
    parser.add_argument('--fail-uncovered', action='store_true', help='With --report-uncovered: exit 1 if any')
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    config_path = args.config or (DEFAULT_CONFIG if repo == ROOT else None)
    config = load_config(config_path)
    try:
        if args.report_uncovered:
            uncovered, missing, dead = report_uncovered(repo, config)
            for path in uncovered:
                print(f'DOC-6  {path}: no docs page covers it')
            for page in missing:
                print(f'DOC-3  {page}: no `covers:` frontmatter')
            for glob in dead:
                print(f'[check-docs-coverage][warn] `covers:` glob {glob!r} matches no tracked file')
            print(f'[check-docs-coverage] {len(uncovered)} uncovered code files, {len(missing)} pages without covers')
            return 1 if args.fail_uncovered and (uncovered or missing) else 0
        violations = check_change(repo, args.base, args.head, config)
    except RuntimeError as exc:
        print(f'[check-docs-coverage][error] {exc}', file=sys.stderr)
        return 2
    for violation in violations:
        print(violation)
    if violations:
        print(f'[check-docs-coverage][error] {len(violations)} violation(s) of docs/regulation.md section 3')
        return 1
    print(f'[check-docs-coverage] ok: changed code is covered by changed docs pages ({args.base}...{args.head})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
