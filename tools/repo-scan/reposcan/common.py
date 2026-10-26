"""Shared helpers: safe git calls, file listing, URL and secret handling, JSON output."""
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit

GIT_TIMEOUT = 60
MAX_TEXT_BYTES = 512 * 1024
SKIP_DIRS = {'.git', 'node_modules', '.venv', 'venv', '__pycache__', '.mypy_cache', '.pytest_cache', '.ruff_cache',
             '.tox', 'dist', 'build', 'target', 'vendor', '.idea', '.vscode', '.agentic'}
# Names that look like credentials. Values under such keys are never stored.
SECRET_NAME = re.compile(r'pass(word)?|passwd|pwd|secret|token|api[_-]?key|private[_-]?key|credential|auth[_-]?key'
                         r'|access[_-]?key|client[_-]?secret|cookie|session[_-]?key|dsn', re.I)


def git(repo, *args, timeout=GIT_TIMEOUT):
    """Run a read-only git command. Hooks and fsmonitor are off, so no repository code runs."""
    cmd = ['git', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=/dev/null', '-C', str(repo), *args]
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def list_files(repo):
    """Tracked files (relative POSIX paths). Falls back to a filtered walk when git has no index."""
    out = git(repo, 'ls-files', '-z')
    if out:
        return sorted(p for p in out.split('\0') if p and (Path(repo) / p).is_file())
    files = []
    for root, dirs, names in os.walk(repo):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in names:
            files.append(Path(root, name).relative_to(repo).as_posix())
    return sorted(files)


def read_text(path, limit=MAX_TEXT_BYTES):
    try:
        with open(path, 'rb') as fh:
            data = fh.read(limit + 1)
    except OSError:
        return None
    if len(data) > limit or b'\0' in data[:4096]:
        return None
    return data.decode('utf-8', errors='replace')


def line_of(text, pattern, flags=re.M):
    """1-based line number of the first regex match, or None."""
    m = re.search(pattern, text, flags)
    return text.count('\n', 0, m.start()) + 1 if m else None


def sanitize_url(url):
    """Drop user info (tokens) from a URL; keep scheme, host, port and path."""
    if not url:
        return url
    url = url.strip()
    if '://' in url:
        parts = urlsplit(url)
        host = parts.hostname or ''
        if parts.port:
            host = f'{host}:{parts.port}'
        return f'{parts.scheme}://{host}{parts.path}'
    if '@' in url:  # scp-like git@host:path
        return url.split('@', 1)[1]
    return url


def url_host(value):
    """Host of a URL-like value, or None. Never returns credentials or paths."""
    value = (value or '').strip().strip('"\'')
    if '://' not in value:
        return None
    try:
        host = urlsplit(value).hostname
    except ValueError:
        return None
    if not host or '$' in host or '{' in host:
        return None
    return host.lower()


def remote_key(url):
    """Normalize a git remote or web URL to 'host/path' (lowercase, no .git, no port, no credentials)."""
    if not url:
        return None
    url = url.strip()
    if '://' in url:
        parts = urlsplit(url)
        host, path = parts.hostname or '', parts.path
    elif re.match(r'^[\w.-]+@[\w.-]+:', url):
        host, path = url.split('@', 1)[1].split(':', 1)
    elif re.match(r'^[\w.-]+\.[a-z]{2,}/', url):
        host, path = url.split('/', 1)
    else:
        return None
    path = re.sub(r'\.git/?$', '', path.strip('/'))
    return f'{host.lower()}/{path.lower()}' if host and path else None


REDACT_PATTERNS = [
    (re.compile(r'(?i)\b([A-Z0-9_]*(?:PASS(?:WORD)?|SECRET|TOKEN|API_?KEY|PRIVATE_?KEY|CREDENTIALS?)[A-Z0-9_]*)'
                r'(\s*[:=]\s*)\S+'), r'\1\2***'),
    (re.compile(r'://[^/\s:@]+:[^/\s@]+@'), '://***@'),
    (re.compile(r'\bsk-[A-Za-z0-9_-]{8,}'), 'sk-***'),
    (re.compile(r'\b(?:ghp|glpat|xox[bap])[-_A-Za-z0-9]{10,}'), '***'),
    (re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----'), '***'),
]


def redact(text):
    for pattern, repl in REDACT_PATTERNS:
        text = pattern.sub(repl, text)
    return text


def norm_pkg(name):
    """PEP 503 style normalization, also used for npm and service names."""
    return re.sub(r'[-_.]+', '-', name.strip().lower())


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + '\n')
    tmp.replace(path)


def load_json(path):
    with open(path) as fh:
        return json.load(fh)


def git_exclude(repo, pattern):
    """Add a pattern to the repository's local .git/info/exclude (never to a tracked file)."""
    rel = git(repo, 'rev-parse', '--git-path', 'info/exclude')
    if not rel:
        return False
    path = Path(rel.strip())
    if not path.is_absolute():
        path = Path(repo) / path
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text() if path.exists() else ''
    if pattern in existing.splitlines():
        return True
    with open(path, 'a') as fh:
        if existing and not existing.endswith('\n'):
            fh.write('\n')
        fh.write(pattern + '\n')
    return True


def is_tracked(repo, rel):
    return bool(git(repo, 'ls-files', '--error-unmatch', rel))
