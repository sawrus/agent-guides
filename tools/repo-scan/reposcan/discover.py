"""Repository discovery, path-to-URL mapping, git facts and activity class."""
import datetime as dt
import os
from pathlib import Path
import re

from .common import SKIP_DIRS, git, remote_key, sanitize_url

DOMAIN = re.compile(r'^[a-z0-9-]+(\.[a-z0-9-]+)+$', re.I)


def find_repos(roots):
    """Directories that contain .git (dir or file). Nested repositories inside a repo are not followed."""
    found = []
    for root in roots:
        root = Path(root).expanduser().resolve()
        if (root / '.git').exists():
            found.append(root)
            continue
        for current, dirs, files in os.walk(root):
            if '.git' in dirs or '.git' in files:
                found.append(Path(current))
                dirs[:] = []
                continue
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith('.'))
    return sorted(set(found))


def expected_url(path, root=None, remote_host=None):
    """`~/work/<host>/<path>` -> ('<host>/<path>', 'https://<host>/<path>').

    The host segment is the one equal to the remote host when there is one; otherwise the last domain-like
    segment of the scan root (or of the path), so `/home/first.last/work/<host>/...` still maps to <host>.
    """
    parts = Path(path).resolve().parts
    candidates = [i for i, part in enumerate(parts[:-1]) if DOMAIN.match(part)]
    exact = [i for i in candidates if remote_host and parts[i].lower() == remote_host.lower()]
    if exact:
        candidates = exact
    elif root is not None:
        depth = len(Path(root).resolve().parts)
        candidates = [i for i in candidates if i < depth] or candidates
    if not candidates:
        return None, None
    i = candidates[-1]
    rest = '/'.join(parts[i + 1:])
    return f'{parts[i].lower()}/{rest.lower()}', f'https://{parts[i]}/{rest}'


def identity(path, root, root_url=None, remote=None):
    """GitLab URL that identifies a repository.

    Order: `--root-url <root>=<url>` + path below the root; inference from `.../<host>/<path>`;
    the origin remote; a file:// URL as the last resort. Returns {url, key, source}; key is 'host/path' lowercase.
    """
    path, root = Path(path).resolve(), Path(root).resolve() if root else None
    if root_url and root is not None:
        rel = path.relative_to(root).as_posix()
        url = root_url.rstrip('/') + ('' if rel == '.' else '/' + rel)
        return {'url': url, 'key': remote_key(url), 'source': 'root-url'}
    remote_host = (remote or '').split('/')[0] or None
    key, url = expected_url(path, root, remote_host)
    if url:
        return {'url': url, 'key': key, 'source': 'path'}
    if remote:
        return {'url': f'https://{remote}', 'key': remote, 'source': 'remote'}
    return {'url': path.as_uri(), 'key': None, 'source': 'local'}


def git_facts(repo, now, window_days):
    since = (now - dt.timedelta(days=window_days)).strftime('%Y-%m-%dT%H:%M:%S')
    head = (git(repo, 'rev-parse', 'HEAD') or '').strip() or None
    last = (git(repo, 'log', '-1', '--format=%cI') or '').strip() or None
    count = git(repo, 'rev-list', '--count', f'--since={since}', 'HEAD') if head else None
    remote = (git(repo, 'remote', 'get-url', 'origin') or '').strip() or None
    branch = (git(repo, 'rev-parse', '--abbrev-ref', 'HEAD') or '').strip() or None
    return {
        'head': head,
        'branch': branch,
        'last_commit': last,
        'commits_window': int(count) if count and count.strip().isdigit() else 0,
        'remote_url': sanitize_url(remote) if remote else None,
        'remote_key': remote_key(remote) if remote else None,
    }


def classify(rel_parts, name, facts, has_ci, code_lines, cfg, doc_lines=0, doc_files=0):
    """Return (class, reasons). Rules come from applicability.json -> activity.

    code_lines counts code and config; doc_lines and doc_files count Markdown/reST/AsciiDoc. A repository with a
    single README (for example the GitLab template of an empty project) is not a documentation repository.
    """
    segments = [p.lower() for p in rel_parts]
    reasons = []
    archived = sorted(set(segments) & set(cfg['archived_segments']))
    if archived:
        return 'archived', [f'path segment: {s}' for s in archived]
    junk = sorted(set(segments) & set(cfg['junk_segments']))
    if junk:
        return 'junk', [f'path segment: {s}' for s in junk]
    if name.lower() in cfg['junk_names']:
        return 'junk', [f'repository name: {name}']
    if name.lower() in cfg['docs_names']:
        return 'docs', [f'repository name: {name}']
    if not facts['head']:
        return 'junk', ['no readable HEAD (empty repository or broken worktree link)']
    if (doc_files >= cfg['docs_min_doc_files'] and doc_lines >= cfg['docs_min_doc_lines']
            and code_lines <= cfg['docs_max_code_lines']
            and doc_lines >= cfg['docs_min_ratio'] * code_lines):
        return 'docs', [f'{doc_lines} documentation lines, {code_lines} code+config lines']
    if not has_ci and code_lines < cfg['junk_max_code_lines']:
        return 'junk', [f'no CI and {code_lines} code+config lines (< {cfg["junk_max_code_lines"]})']
    commits = facts['commits_window']
    window = f'{cfg["window_days"]} days'
    if commits >= cfg['active_min_commits'] and (has_ci or commits >= cfg['active_min_commits_without_ci']):
        reasons.append(f'{commits} commits in {window}')
        if has_ci:
            reasons.append('has CI')
        return 'active', reasons
    reasons.append(f'{commits} commits in {window}')
    if not has_ci:
        reasons.append('no CI')
    return 'stale', reasons
