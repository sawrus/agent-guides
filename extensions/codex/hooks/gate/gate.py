#!/usr/bin/env python3
"""Agentic quality gate for Claude Code, Codex, and OpenCode (docs/agentic-v2-lean/README.md).

`--event stop`: when the working tree changed since install (`.agentic/gate/baseline.json` holds the hashes of
files that were uncommitted then), run the project checks; on failure ask the agent to continue
with the output (Stop `{"decision": "block", "reason": ...}`). It also asks once for a CHANGELOG entry when
source files changed. `--event guard`: deny secret reads, force pushes, and recursive deletes outside the
project (PreToolUse `permissionDecision: deny`). Settings: optional `.agent/gate.json`
{"commands": ["make test"], "changelog": true, "max_blocks": 3}. Standard library only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import time

RUNTIME_DIRS = ('.agentic/', '.agentic-blackbox/', '.reviews/', '.git/')
NOT_SOURCE = re.compile(r'(^|/)(tests?|docs?)/|(^|/)test_[^/]*$|_test\.\w+$|\.md$|^CHANGELOG')
SECRET = re.compile(r'(^|/)\.env(\.(?!example$|sample$|template$)[^/]*)?$|(^|/)(id_rsa|id_ed25519)$|\.pem$')
FORCE_PUSH = re.compile(r'\bgit\s+push\b.*(\s--force(?!-with-lease)\b|\s-f\b)')
RECURSIVE_RM = re.compile(r'\brm\s+(-\w*r\w*f\w*|-\w*f\w*r\w*|--recursive)\b')
CHECK_TIMEOUT = 600
TAIL_LINES = 40


def settings(project):
    try:
        data = json.loads((project / '.agent/gate.json').read_text())
    except (OSError, ValueError):
        data = {}
    if 'commands' not in data:
        targets = make_targets(project)
        data['commands'] = [f'make {t}' for t in ('test', 'lint') if t in targets]
    data.setdefault('changelog', True)
    data.setdefault('max_blocks', 3)
    return data


def make_targets(project):
    try:
        text = (project / 'Makefile').read_text()
    except OSError:
        return set()
    return set(re.findall(r'^([A-Za-z][\w-]*)\s*:(?!=)', text, re.M))


def changed_files(project):
    try:
        out = subprocess.run(['git', '-C', str(project), 'status', '--porcelain', '--untracked-files=all'],
                             capture_output=True, text=True, timeout=30, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    files = [line[3:].strip('"').split(' -> ')[-1] for line in out.splitlines()]
    files = [f for f in files if not f.startswith(RUNTIME_DIRS) and '__pycache__/' not in f and not f.endswith('.pyc')]
    baseline = install_baseline(project)
    return [f for f in files if f not in baseline or baseline[f] != file_hash(project / f)]


def install_baseline(project):
    try:
        files = json.loads((project / '.agentic/gate/baseline.json').read_text()).get('files')
    except (OSError, ValueError, AttributeError):
        return {}
    return files if isinstance(files, dict) else {}


def file_hash(path):
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def changelog_updated(project, changed):
    if 'CHANGELOG.md' not in changed:
        return False
    try:
        diff = subprocess.run(['git', '-C', str(project), 'diff', 'HEAD', '--', 'CHANGELOG.md'],
                              capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return True
    return any(line.startswith('+') and not line.startswith('+++') and line[1:].strip() for line in diff.splitlines()) \
        or not diff  # untracked new file


def run_check(project, command):
    started = time.monotonic()
    try:
        result = subprocess.run(command, shell=True, cwd=project, capture_output=True, text=True, timeout=CHECK_TIMEOUT)
        code, output = result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        code, output = 124, f'timed out after {CHECK_TIMEOUT}s'
    tail = '\n'.join(output.strip().splitlines()[-TAIL_LINES:])
    return {'command': command, 'exit': code, 'seconds': round(time.monotonic() - started, 1), 'tail': tail}


def state_path(project):
    return project / '.agentic/gate/state.json'


def load_state(project):
    try:
        return json.loads(state_path(project).read_text())
    except (OSError, ValueError):
        return {}


def save(project, name, data):
    path = project / '.agentic/gate' / name
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    except OSError:
        pass


def stop(project, payload):
    config = settings(project)
    changed = changed_files(project)
    session = str(payload.get('session_id') or 'default')
    state = load_state(project)
    record = state.get(session, {'blocks': 0, 'changelog_asked': False})
    evidence = {'time': time.strftime('%Y-%m-%dT%H:%M:%S'), 'session': session, 'changed': changed[:50], 'checks': []}
    reason = None
    if changed and config['commands']:
        evidence['checks'] = [run_check(project, c) for c in config['commands']]
        failed = [c for c in evidence['checks'] if c['exit'] != 0]
        if failed:
            first = failed[0]
            reason = (f"Agentic gate: `{first['command']}` failed (exit {first['exit']}). Fix the cause and run it again, "
                      f"or explain in your report why it cannot pass.\n\n{first['tail']}")
    source_changed = [f for f in changed if not NOT_SOURCE.search(f)]
    if (not reason and config['changelog'] and source_changed and not record['changelog_asked']
            and (project / 'CHANGELOG.md').is_file() and not changelog_updated(project, changed)):
        record['changelog_asked'] = True
        reason = ('Agentic gate: source files changed but CHANGELOG.md has no new entry. Add a line under Unreleased '
                  'for a user-visible change, or state in your report why the change is not user-visible.')
    evidence['passed'] = reason is None
    if reason and record['blocks'] >= config['max_blocks']:
        evidence['released'] = 'max_blocks reached; the agent must report the open failure'
        reason = None
    if reason:
        record['blocks'] += 1
    else:
        record['blocks'] = 0
    state[session] = record
    save(project, 'state.json', state)
    save(project, 'last.json', evidence)
    return {'decision': 'block', 'reason': reason} if reason else {}


def guard_reason(project, payload):
    data = payload.get('tool_input') or payload.get('args') or {}
    command = str(data.get('command') or data.get('cmd') or '') if isinstance(data, dict) else ''
    paths = [str(data.get(k)) for k in ('file_path', 'path', 'filePath') if isinstance(data, dict) and data.get(k)]
    if command:
        if FORCE_PUSH.search(command):
            return 'Agentic guard: force push is blocked. Use a new commit or `--force-with-lease` after the user approves.'
        if RECURSIVE_RM.search(command) and outside(project, command):
            return 'Agentic guard: recursive delete outside the project is blocked.'
        paths += [token for token in split(command) if '/' in token or token.startswith('.env')]
    for raw in paths:
        if SECRET.search(raw.strip('\'"')):
            return f'Agentic guard: `{raw}` may hold secrets; reading or editing it is blocked. Ask the user for the needed value.'
    return None


def split(command):
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def outside(project, command):
    root = project.resolve()
    scratch = Path(tempfile.gettempdir()).resolve()
    for token in split(command):
        if token.startswith('-') or token in ('rm', 'sudo'):
            continue
        target = Path(token).expanduser()
        target = (target if target.is_absolute() else root / target).resolve()
        if scratch in target.parents:
            continue
        if target == root or root not in target.parents:
            return True
    return False


def guard(project, payload):
    reason = guard_reason(project, payload)
    if not reason:
        return {}
    return {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
                                   'permissionDecisionReason': reason}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--event', choices=('stop', 'guard'), required=True)
    parser.add_argument('--project-dir', default='.')
    args = parser.parse_args(argv)
    try:
        payload = json.loads(sys.stdin.read() or '{}')
    except ValueError:
        payload = {}
    project = Path(args.project_dir or payload.get('cwd') or '.')
    try:
        result = stop(project, payload) if args.event == 'stop' else guard(project, payload)
    except Exception as error:  # a gate bug must never trap the agent
        print(f'agentic gate error: {error}', file=sys.stderr)
        return 0
    if result:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
