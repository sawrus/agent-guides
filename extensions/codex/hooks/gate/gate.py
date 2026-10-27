#!/usr/bin/env python3
"""Agentic quality gate for Claude Code, Codex, and OpenCode (docs/agentic-v2-lean/README.md).

`--event stop`: when the working tree changed since install (`.agentic/gate/baseline.json` holds the hashes of
files that were uncommitted then), run the project checks; on failure ask the agent to continue
with the output (Stop `{"decision": "block", "reason": ...}`). It also asks once for a CHANGELOG entry when
source files changed. Every Stop writes `.agentic/gate/last.json` with `accepted` and `reason_code`.
`--event guard`: deny secret reads, force pushes, and recursive deletes outside the project (PreToolUse
`permissionDecision: deny`); ask the user before commands that touch production (`guard.confirm`). Codex hooks
cannot ask, so on Codex a confirm rule denies. The database guard reads the Bash command, its heredocs, and the
script files it runs: write or maintenance SQL against a non-local database is denied, a connection with
credentials from the environment (.env) asks, and plan mode denies any non-local connection (`guard.db`).
Settings: optional `.agent/gate.json` {"commands": ["make test"], "changelog": true, "max_blocks": 3,
"guard": {"defaults": true, "confirm": [...], "prod_context_pattern": "prod", "prod_hosts": [],
"db": {"mode": "ask", "write": "deny"}}}. Standard library only.
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

# Database guard: signals in the Bash command, its heredocs, and the script files it runs.
DB_CLIENTS = ('psql', 'pg_dump', 'pg_restore', 'mysql', 'mysqldump', 'redis-cli', 'mongosh', 'clickhouse-client')
DB_CLIENT_WORD = re.compile(r'(?<![\w.-])(?:' + '|'.join(map(re.escape, DB_CLIENTS)) + r')(?![\w.-])')
DB_CONNECT = re.compile(
    r'\bpsycopg2?\s*\.\s*(?:connect|(?:Async)?Connection\s*\.\s*connect)\b'
    r'|\bfrom\s+(?:psycopg2?|asyncpg|pymysql)\s+import\b[^\n]*\bconnect\b'
    r'|\basyncpg\s*\.\s*(?:connect|create_pool)\b|\bcreate_(?:async_)?engine\s*\('
    r'|\bpymysql\s*\.\s*connect\b|\bmysql\s*\.\s*connector\s*\.\s*connect\b'
    r'|\bredis\s*\.\s*(?:Strict)?Redis\s*\(|\bredis\s*\.\s*from_url\b'
    r'|\bpymongo\s*\.\s*MongoClient\b|\bMongoClient\s*\(|\bclickhouse_connect\b')
DB_ENV_NAME = r'\w*(?:DSN|DATABASE_URL|DB_|PG|PSQL|MYSQL|REDIS|MONGO)\w*'
ENV_CREDS = re.compile(
    r'\b(?:load_dotenv|dotenv_values|find_dotenv)\b|\bdotenv\b[^\n]{0,40}\bconfig\b'
    r'|(?:^|[\s;&|(])(?:source|\.)\s+[\'"]?[^\s;&|\'"]*\.env\b|--env-file\b|\$\(\s*cat\s+[^\s)]*\.env\b'
    rf'|\bos\s*\.\s*(?:environ\s*(?:\.\s*get\s*\(|\[)|getenv\s*\()\s*[\'"]{DB_ENV_NAME}[\'"]'
    rf'|\bprocess\s*\.\s*env\s*(?:\.|\[\s*[\'"]){DB_ENV_NAME}|\$\{{?{DB_ENV_NAME}', re.M)
DB_URL = re.compile(r'\b(?:postgres(?:ql)?|mysql|mariadb|rediss?|mongodb(?:\+srv)?|clickhouse)(?:\+\w+)?://'
                    r'(?:[^@/\s\'"]*@)?(\[[^\]\s]*\]|[^:/?,\s\'"]*)', re.I)
HOST_KEY = re.compile(r'\bhost\s*=\s*[\'"]?([^\s\'",;)]+)', re.I)
SQLITE = re.compile(r'\bsqlite', re.I)
LOCAL_HOSTS = ('', 'localhost', '::1', '0.0.0.0', 'host.docker.internal')
WRITE_SQL = re.compile(r'''(?:
    \bVACUUM\b | \bREINDEX\b | \bREFRESH\s+MATERIALIZED\s+VIEW\b
  | \bCLUSTER(?:\s+VERBOSE)?(?:\s+[\w."]+(?:\s+USING\s+[\w."]+)?)?\s*[;"']
  | \bDROP\s+(?:TABLE|INDEX|VIEW|MATERIALIZED\s+VIEW|SCHEMA|DATABASE|ROLE|USER|EXTENSION|FUNCTION|TRIGGER
              |SEQUENCE|TYPE|OWNED|COLUMN|CONSTRAINT)\b
  | \bTRUNCATE\s+(?:TABLE\s+)?(?:ONLY\s+)?[\w."] | \bDELETE\s+FROM\b | \bINSERT\s+INTO\b | \bMERGE\s+INTO\b
  | \bUPDATE\s+(?:ONLY\s+)?[\w."]+\s+SET\b
  | \bALTER\s+(?:TABLE|INDEX|SYSTEM|DATABASE|ROLE|USER|SCHEMA|SEQUENCE|VIEW|MATERIALIZED\s+VIEW)\b
  | \bCREATE\s+(?:UNIQUE\s+)?INDEX\b | \bCREATE\s+(?:TABLE|EXTENSION|ROLE|USER|SCHEMA|DATABASE)\b
  | \b(?:GRANT|REVOKE)\s+(?:ALL|SELECT|INSERT|UPDATE|DELETE|TRUNCATE|REFERENCES|TRIGGER|USAGE|EXECUTE|CONNECT
                         |CREATE|TEMP|TEMPORARY)\b[\w\s,()]{0,200}?\b(?:ON|TO|FROM)\b
  | \bCOPY\s+[\w."]+(?:\s*\([^)]{0,500}\))?\s+FROM\b
  | \bpg_(?:terminate|cancel)_backend\b
  | \bdefault_transaction_read_only\s*(?:=|TO)\s*'?off\b
  | \bTRANSACTION\s+READ\s+WRITE\b
)''', re.I | re.X)
WRITE_NOSQL = re.compile(r'\bFLUSH(?:ALL|DB)\b|\.flush(?:all|db)\s*\(|\bDEL\s+\S|\.drop\(\s*\)'
                         r'|\.drop_(?:collection|database)\s*\(|\.dropDatabase\s*\('
                         r'|\.(?:deleteMany|updateMany|delete_many|update_many)\s*\(')
ANALYZE = re.compile(r'\bANALY[SZ]E(?:\s+VERBOSE)?(?:\s+[\w."]+(?:\s*\([^)]{0,500}\))?)?\s*[;"\']', re.I)
HEREDOC = re.compile(r'<<-?[ \t]*([\'"]?)([A-Za-z_]\w*)\1[^\n]*\n.*?(?:^[ \t]*\2[ \t]*$|\Z)', re.S | re.M)
EXPLAIN_BEFORE = re.compile(r'EXPLAIN\s*(?:\([^)]*)?$', re.I)
INTERPRETERS = re.compile(r'^(?:python[\d.]*|pypy3?|node|bash|sh|zsh|ruby|psql)$')
SCRIPT_SUFFIXES = ('.py', '.js', '.mjs', '.cjs', '.sh', '.sql', '.rb')
SCRIPT_BYTES = 256 * 1024
MAX_SCRIPTS = 8


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


def shell_part(command):
    """The command without heredoc bodies: they are input data, not shell syntax."""
    return HEREDOC.sub(lambda m: m.group(0).split('\n', 1)[0] + '\n', command) if '<<' in command else command


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


class NameMatch:
    """A `names` argument for `program()` that matches a basename with a regex."""
    def __init__(self, pattern):
        self.pattern = pattern

    def __contains__(self, name):
        return bool(self.pattern.match(name))


def script_texts(project, command):
    """(suffix, first 256 KB) of the script files the command runs with an interpreter; follows `cd <dir>`."""
    base, texts, seen = project, [], set()
    for tokens in segments(shell_part(command)):
        if tokens[:1] == ['cd'] and len(tokens) > 1:
            target = Path(tokens[1]).expanduser()
            base = target if target.is_absolute() else base / target
            continue
        found = program(tokens, NameMatch(INTERPRETERS))
        for arg in found[1] if found else []:
            arg = arg[len('--file='):] if arg.startswith('--file=') else arg
            if not arg.endswith(SCRIPT_SUFFIXES) or len(texts) >= MAX_SCRIPTS:
                continue
            path = Path(arg).expanduser()
            path = path if path.is_absolute() else base / path
            if path in seen:
                continue
            seen.add(path)
            try:
                with open(path, 'rb') as handle:
                    texts.append((path.suffix, handle.read(SCRIPT_BYTES).decode('utf-8', 'replace')))
            except OSError:
                continue
    return texts


def client_target(tokens):
    """(client, hosts, unknown) when the simple command runs a database CLI; host '' is the local default."""
    found = program(tokens, DB_CLIENTS)
    if not found:
        return None
    tool, args, env = found
    hosts = db_hosts(args, env) + [m.group(1) for arg in args for m in DB_URL.finditer(arg)]
    if hosts:
        return tool, hosts, False
    if any('$' in arg for arg in args):
        return tool, [], True  # the target comes from a shell variable
    variable = {'psql': 'PGHOST', 'pg_dump': 'PGHOST', 'pg_restore': 'PGHOST',
                'mysql': 'MYSQL_HOST', 'mysqldump': 'MYSQL_HOST'}.get(tool)
    return tool, [os.environ.get(variable, '') if variable else ''], False


def is_local(host):
    host = host.strip('[]\'"').lower()
    return host in LOCAL_HOSTS or host.startswith(('127.', '/', '%2f'))


def write_statement(text):
    """The first write or maintenance statement in the text, shortened; None for read-only text."""
    match = WRITE_SQL.search(text) or WRITE_NOSQL.search(text)
    if not match:
        match = next((m for m in ANALYZE.finditer(text)
                      if not EXPLAIN_BEFORE.search(text[max(0, m.start() - 200):m.start()])), None)
    return ' '.join(match.group(0).split())[:60].strip(';"\' ') if match else None


def db_config(project):
    guard_config = settings(project).get('guard')
    config = guard_config.get('db') if isinstance(guard_config, dict) else None
    config = config if isinstance(config, dict) else {}
    mode = config.get('mode') if config.get('mode') in ('ask', 'deny', 'off') else 'ask'
    write = config.get('write') if config.get('write') in ('ask', 'deny') else 'deny'
    return mode, write


def db_decision(project, payload, command):
    """('deny' | 'ask', reason) for a command that reaches a non-local database; None otherwise."""
    mode, write_mode = db_config(project)
    if mode == 'off':
        return None
    scripts = script_texts(project, command)
    text = '\n'.join([command] + [content for _, content in scripts])
    shell_lines = [line for suffix, content in scripts if suffix == '.sh'
                   for line in content.splitlines() if DB_CLIENT_WORD.search(line)][:50]
    hosts, unknown, clients = [], False, 0
    for tokens in segments(shell_part(command)) + [tokens for line in shell_lines for tokens in segments(line)]:
        found = client_target(tokens)
        if found:
            clients += 1
            hosts += found[1]
            unknown = unknown or found[2]
    if not clients and not DB_CONNECT.search(text):
        return None
    hosts += [m.group(1) for m in DB_URL.finditer(text)] + HOST_KEY.findall(text)
    creds = bool(ENV_CREDS.search(text))
    if creds or unknown:
        local = False  # the gate cannot see the target that the environment or .env supplies
    elif hosts:
        local = all(map(is_local, hosts))
    else:
        local = bool(SQLITE.search(text))  # a library connection with no visible target is not local
    if local:
        return None
    statement = write_statement(text)
    plan = payload.get('permission_mode') == 'plan' or payload.get('agent') == 'plan'
    if statement and write_mode == 'deny':
        return 'deny', (f'write or maintenance SQL (`{statement}`) against a non-local database is blocked; '
                        'show the statement to the user and let them run it')
    if plan:
        return 'deny', ('the host is in plan (read-only) mode and the command connects to a non-local database; '
                        'show the command to the user and let them run it')
    if statement:
        return 'ask', f'the command runs write or maintenance SQL (`{statement}`) against a non-local database'
    if creds:
        reason = 'the command connects to a database configured in the environment (.env), which may be production'
        return ('deny', f'{reason}; show the command to the user and let them run it') if mode == 'deny' \
            else ('ask', reason)
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
    custom = guard_config.get('confirm')
    custom = [rule for rule in custom if rule != 'default'] if isinstance(custom, list) else []
    rules = (['default'] if guard_config.get('defaults', True) is not False else []) + custom
    for rule in rules:
        if rule == 'default':
            prod = compile_pattern(guard_config.get('prod_context_pattern') or 'prod')
            hosts = [p for p in map(compile_pattern, guard_config.get('prod_hosts') or []) if p]
            for tokens in segments(shell_part(command)):
                reason = (prod and kube_reason(tokens, prod)) or db_reason(tokens, hosts)
                if reason:
                    return reason
        elif isinstance(rule, dict) and rule.get('pattern'):
            pattern = compile_pattern(rule['pattern'])
            if pattern and pattern.search(command):
                return str(rule.get('reason') or f'the command matches `{rule["pattern"]}`')
    return None


def decision(kind, reason):
    return {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': kind,
                                   'permissionDecisionReason': reason}}


def ask(found, host, suffix):
    """Ask on Claude Code and OpenCode; Codex hooks cannot ask, so deny and send the agent to the user."""
    if host in ASK_HOSTS:
        return decision('ask', f'Agentic guard: {found}{suffix}')
    return decision('deny', f'Agentic guard: {found}. This host cannot ask for confirmation, so the command is '
                            'blocked. Show the command to the user and ask them to run it themselves.')


def guard(project, payload, host=None):
    reason = guard_reason(project, payload)
    if reason:
        return decision('deny', reason)
    data = payload.get('tool_input') or payload.get('args') or {}
    command = str(data.get('command') or data.get('cmd') or '') if isinstance(data, dict) else ''
    if not command:
        return {}
    found = db_decision(project, payload, command)
    if found:
        kind, text = found
        return decision('deny', f'Agentic guard: {text}.') if kind == 'deny' else ask(text, host, '; confirm.')
    found = confirm_reason(project, command)
    if not found:
        return {}
    return ask(found, host, '. Confirm that this production access is intended.')


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
