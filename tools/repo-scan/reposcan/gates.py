"""Quality gate candidates (.agent/gate.json, read by extensions/codex/hooks/gate/gate.py).

`propose` reads Makefile and CI only. `verify` runs the candidate commands in repositories that the user
names explicitly; it keeps only passing commands and writes `.agent/gate.json` locally (git-excluded).
"""
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

from .common import git_exclude, is_tracked, list_files, read_text
from .manifests import parse_gitlab_ci, parse_github_workflow, parse_makefile

MAKE_ORDER = ('test', 'lint', 'check', 'typecheck', 'test-unit', 'unit-test', 'tests')
CHECK_CMD = re.compile(r'^(poetry run |uv run |pipenv run |python -m |python3 -m )?'
                       r'(pytest|ruff( check)?|black --check|mypy|flake8|pylint|isort --check|go test|go vet|'
                       r'golangci-lint|npm (run )?(test|lint)|yarn (test|lint)|pnpm (test|lint)|cargo (test|clippy)|'
                       r'tox|pre-commit run)\b')
CI_CHECK_JOB = re.compile(r'test|lint|check|verify|qa', re.I)


def propose_for(repo, files=None):
    repo = Path(repo)
    files = files if files is not None else list_files(repo)
    sources, commands = [], []
    makes = [(rel, read_text(repo / rel)) for rel in files
             if '/' not in rel and (rel in ('Makefile', 'makefile', 'GNUmakefile') or rel.endswith('.mk'))]
    targets = parse_makefile([(r, t) for r, t in makes if t]).get('targets', {})
    for name in MAKE_ORDER:
        if name in targets and len(commands) < 2:
            if name in ('check', 'typecheck', 'test-unit', 'unit-test', 'tests') and commands:
                continue
            commands.append(f'make {name}')
            sources.append({'command': f'make {name}', 'path': targets[name]['path'], 'line': targets[name]['line']})
    notes = []
    if not commands:
        ci_cmds = []
        if '.gitlab-ci.yml' in files:
            ci = parse_gitlab_ci('.gitlab-ci.yml', read_text(repo / '.gitlab-ci.yml') or '')
            for job in ci['jobs']:
                if CI_CHECK_JOB.search(job['name']) or CI_CHECK_JOB.search(job.get('stage') or ''):
                    ci_cmds += [(c['cmd'], '.gitlab-ci.yml', c['line'], job['name']) for c in job['script']]
        for rel in files:
            if rel.startswith('.github/workflows/') and rel.endswith(('.yml', '.yaml')):
                wf = parse_github_workflow(rel, read_text(repo / rel) or '')
                ci_cmds += [(c['cmd'], rel, c['line'], 'run') for c in wf['runs']]
        for cmd, rel, line, job in ci_cmds:
            if CHECK_CMD.match(cmd) and '$' not in cmd and cmd not in commands:
                commands.append(cmd)
                sources.append({'command': cmd, 'path': rel, 'line': line, 'job': job})
        if commands:
            notes.append('commands come from CI scripts; they may need CI variables or installed tools')
    if not commands:
        notes.append('no test or lint command found; gate.py would run nothing')
    gate = {'commands': commands, 'changelog': 'CHANGELOG.md' in files, 'max_blocks': 3}
    existing = None
    if '.agent/gate.json' in files:
        try:
            existing = json.loads((repo / '.agent/gate.json').read_text())
        except (OSError, ValueError):
            existing = 'unreadable'
    return {'gate': gate, 'sources': sources, 'notes': notes, 'existing_tracked_gate': existing}


def run_command(repo, command, timeout):
    started = time.monotonic()
    proc = subprocess.Popen(command, shell=True, cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, start_new_session=True)
    try:
        output, _ = proc.communicate(timeout=timeout)
        code = proc.returncode
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
        output, _ = proc.communicate()
        code = 124
        output = (output or '') + f'\ntimed out after {timeout}s'
    tail = '\n'.join((output or '').strip().splitlines()[-20:])
    return {'command': command, 'exit': code, 'seconds': round(time.monotonic() - started, 1), 'tail': tail}


def verify(repo, timeout=600, write=True, force=False):
    repo = Path(repo).resolve()
    proposal = propose_for(repo)
    results = [run_command(repo, cmd, timeout) for cmd in proposal['gate']['commands']]
    passing = [r['command'] for r in results if r['exit'] == 0]
    gate = dict(proposal['gate'], commands=passing)
    report = {'repo': str(repo), 'proposed': proposal['gate']['commands'], 'results': results, 'gate': gate,
              'written': None}
    if not write:
        return report
    target = repo / '.agent/gate.json'
    if is_tracked(repo, '.agent/gate.json') and not force:
        report['skipped'] = '.agent/gate.json is tracked; use --force to overwrite the working copy'
        return report
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(gate, indent=2) + '\n')
    if not is_tracked(repo, '.agent/gate.json'):
        git_exclude(repo, '.agent/gate.json')
    report['written'] = str(target)
    return report
