#!/usr/bin/env python3
"""Agentic quality gate for Claude Code, Codex, and OpenCode (docs/agentic-v2-lean/README.md).

`--event stop`: when the working tree changed since install (`.agentic/gate/baseline.json` holds the hashes of
files that were uncommitted then), run the project checks; on failure ask the agent to continue
with the output (Stop `{"decision": "block", "reason": ...}`). It also asks once for a CHANGELOG entry when
source files changed. Every Stop writes `.agentic/gate/last.json` with `accepted` and `reason_code`.
`--event guard`: deny secret reads, force pushes, and recursive deletes outside the project (PreToolUse
`permissionDecision: deny`); ask the user before commands that touch production (`guard.confirm`). Codex hooks
cannot ask, so on Codex a confirm rule denies. Settings: optional `.agent/gate.json` {"commands": ["make test"],
"changelog": true, "max_blocks": 3, "guard": {"confirm": [...], "prod_context_pattern": "prod",
"prod_hosts": []}}. Standard library only.
"""
import argparse
import hashlib
import json
import os
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
KUBE_TOOLS = ('kubectl', 'helm', 'oc')
KUBE_CONTEXT_FLAGS = ('--context', '--kube-context')
DB_TOOLS = ('psql', 'pg_dump', 'pg_restore', 'mysql', 'mysqldump')
DB_URI = re.compile(r'^(?:postgres(?:ql)?|mysql)://(?:[^@/]*@)?(\[[^\]]+\]|[^:/?,]+)')
SEPARATORS = {';', '&', '&&', '|', '||', '(', ')', ';;', '|&'}
WRAPPERS = ('sudo', 'env', 'time', 'command', 'exec', 'nohup', 'watch', 'xargs', 'timeout')
ASK_HOSTS = ('claude', 'opencode')


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


def git_head(project):
    try:
        result = subprocess.run(['git', '-C', str(project), 'rev-parse', '--verify', '-q', 'HEAD'],
                                capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return (result.stdout.strip() or None) if result.returncode == 0 else None


def manifest_info(project):
    """Pack version and profile from the installer manifest `.agentic.json`; None when absent."""
    try:
        data = json.loads((project / '.agentic.json').read_text())
    except (OSError, ValueError):
        return None, None
    if not isinstance(data, dict):
        return None, None
    agentic = data.get('_agentic') if isinstance(data.get('_agentic'), dict) else {}
    config = data.get('settings') if isinstance(data.get('settings'), dict) else {}
    return agentic.get('updated_by') or agentic.get('created_by') or None, config.get('profile') or None


def stop(project, payload, host=None):
    config = settings(project)
    changed = changed_files(project)
    session = str(payload.get('session_id') or 'default')
    state = load_state(project)
    record = state.get(session, {'blocks': 0, 'changelog_asked': False})
    pack_version, profile = manifest_info(project)
    evidence = {'time': time.strftime('%Y-%m-%dT%H:%M:%S'), 'session': session, 'changed': changed[:50], 'checks': [],
                'head': git_head(project), 'pack_version': pack_version, 'profile': profile}
    reason = None
    code = 'checks_passed' if changed else 'no_changes'
    if changed and config['commands']:
        evidence['checks'] = [run_check(project, c) for c in config['commands']]
        failed = [c for c in evidence['checks'] if c['exit'] != 0]
        if failed:
            first = failed[0]
            code = 'checks_failed'
            reason = (f"Agentic gate: `{first['command']}` failed (exit {first['exit']}). Fix the cause and run it again, "
                      f"or explain in your report why it cannot pass.\n\n{first['tail']}")
    source_changed = [f for f in changed if not NOT_SOURCE.search(f)]
    if (not reason and config['changelog'] and source_changed and not record['changelog_asked']
            and (project / 'CHANGELOG.md').is_file() and not changelog_updated(project, changed)):
        record['changelog_asked'] = True
        code = 'changelog_missing'
        reason = ('Agentic gate: source files changed but CHANGELOG.md has no new entry. Add a line under Unreleased '
                  'for a user-visible change, or state in your report why the change is not user-visible.')
    evidence['passed'] = reason is None
    if reason and record['blocks'] >= config['max_blocks']:
        evidence['released'] = 'max_blocks reached; the agent must report the open failure'
        record['last_release'] = {'time': evidence['time'], 'cause': code, 'head': evidence['head']}
        code = 'max_blocks'
        reason = None
    evidence['accepted'] = code in ('checks_passed', 'no_changes')
    evidence['reason_code'] = code
    if reason:
        record['blocks'] += 1
    else:
        record['blocks'] = 0
    state[session] = record
    save(project, 'state.json', state)
    save(project, 'last.json', evidence)
    if reason:
        return {'decision': 'block', 'reason': reason}
    if not evidence['accepted'] and host == 'claude':
        return {'systemMessage': f'Agentic gate: NOT ACCEPTED ({code})'}
    return {}


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


def segments(command):
    """Split a shell command into simple commands on `;`, `&&`, `|`, and similar operators."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()
    parts, current = [], []
    for token in tokens:
        if token in SEPARATORS or (token and set(token) <= set(';&|()')):
            if current:
                parts.append(current)
            current = []
        else:
            current.append(token)
    if current:
        parts.append(current)
    return parts


def program(tokens, names):
    """Return (name, args, env) when the simple command runs one of `names`, past env assignments and wrappers."""
    env = {}
    wrapped = False
    for index, token in enumerate(tokens):
        base = token.rsplit('/', 1)[-1]
        if base in names:
            return base, tokens[index + 1:], env
        if re.match(r'^[A-Za-z_]\w*=', token):
            key, _, value = token.partition('=')
            env[key] = value
        elif base in WRAPPERS:
            wrapped = True
        elif not wrapped:  # after a wrapper (`sudo -u x`, `timeout 5`), skip its options and arguments
            return None
    return None


def flag_value(args, flags):
    for index, arg in enumerate(args):
        for flag in flags:
            if arg == flag and index + 1 < len(args):
                return args[index + 1]
            if arg.startswith(flag + '='):
                return arg[len(flag) + 1:]
    return None


def current_context(args, env):
    """`kubectl config current-context` for the command's kubeconfig; None on any failure. Local only, 2 s."""
    command = ['kubectl', 'config', 'current-context']
    kubeconfig = flag_value(args, ('--kubeconfig',))
    if kubeconfig:
        command += ['--kubeconfig', kubeconfig]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=2,
                                env={**os.environ, **{k: v for k, v in env.items() if k == 'KUBECONFIG'}})
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def kube_reason(tokens, prod):
    found = program(tokens, KUBE_TOOLS)
    if not found:
        return None
    tool, args, env = found
    context = flag_value(args, KUBE_CONTEXT_FLAGS)
    if context is not None:
        return f'`{tool}` targets the production context `{context}`' if prod.search(context) else None
    if args[:2] == ['config', 'use-context'] and len(args) > 2:
        return f'`{tool}` switches to the production context `{args[2]}`' if prod.search(args[2]) else None
    context = current_context(args, env)
    if context and prod.search(context):
        return f'`{tool}` runs in the current kubectl context `{context}`, which looks like production'
    return None


def db_hosts(args, env):
    hosts = [env[k] for k in ('PGHOST', 'MYSQL_HOST') if env.get(k)]
    for index, arg in enumerate(args):
        if arg in ('-h', '--host') and index + 1 < len(args):
            hosts.append(args[index + 1])
        elif arg.startswith('--host='):
            hosts.append(arg[len('--host='):])
        elif arg.startswith('-h') and len(arg) > 2:
            hosts.append(arg[2:])
        match = DB_URI.match(arg)
        if match:
            hosts.append(match.group(1).strip('[]'))
        hosts += re.findall(r'(?:^|\s)host=([^\s]+)', arg)
    return hosts


def db_reason(tokens, patterns):
    found = program(tokens, DB_TOOLS) if patterns else None
    if not found:
        return None
    tool, args, env = found
    for host in db_hosts(args, env):
        if any(p.search(host) for p in patterns):
            return f'`{tool}` connects to the production host `{host}`'
    return None


def compile_pattern(text):
    try:
        return re.compile(str(text), re.I)
    except re.error:
        return None


def confirm_reason(project, command):
    """Reason to ask the user before a command that may touch production; None when no rule matches."""
    guard_config = settings(project).get('guard')
    guard_config = guard_config if isinstance(guard_config, dict) else {}
    rules = guard_config.get('confirm', ['default'])
    rules = rules if isinstance(rules, list) else ['default']
    for rule in rules:
        if rule == 'default':
            prod = compile_pattern(guard_config.get('prod_context_pattern') or 'prod')
            hosts = [p for p in map(compile_pattern, guard_config.get('prod_hosts') or []) if p]
            for tokens in segments(command):
                reason = (prod and kube_reason(tokens, prod)) or db_reason(tokens, hosts)
                if reason:
                    return reason
        elif isinstance(rule, dict) and rule.get('pattern'):
            pattern = compile_pattern(rule['pattern'])
            if pattern and pattern.search(command):
                return str(rule.get('reason') or f'the command matches `{rule["pattern"]}`')
    return None


def guard(project, payload, host=None):
    reason = guard_reason(project, payload)
    decision = 'deny'
    if not reason:
        data = payload.get('tool_input') or payload.get('args') or {}
        command = str(data.get('command') or data.get('cmd') or '') if isinstance(data, dict) else ''
        found = confirm_reason(project, command) if command else None
        if not found:
            return {}
        if host in ASK_HOSTS:
            decision = 'ask'
            reason = f'Agentic guard: {found}. Confirm that this production access is intended.'
        else:
            reason = (f'Agentic guard: {found}. This host cannot ask for confirmation, so the command is blocked. '
                      'Show the command to the user and ask them to run it themselves.')
    return {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': decision,
                                   'permissionDecisionReason': reason}}


def detect_host(value):
    if value:
        return value
    return 'claude' if os.environ.get('CLAUDE_PROJECT_DIR') else None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--event', choices=('stop', 'guard'), required=True)
    parser.add_argument('--project-dir', default='.')
    parser.add_argument('--host', choices=('claude', 'codex', 'opencode'))
    args = parser.parse_args(argv)
    try:
        payload = json.loads(sys.stdin.read() or '{}')
    except ValueError:
        payload = {}
    project = Path(args.project_dir or payload.get('cwd') or '.')
    host = detect_host(args.host)
    try:
        result = stop(project, payload, host) if args.event == 'stop' else guard(project, payload, host)
    except Exception as error:  # a gate bug must never trap the agent
        print(f'agentic gate error: {error}', file=sys.stderr)
        return 0
    if result:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
