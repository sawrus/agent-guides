"""Command line: scan | gate-propose | gate-verify | llm."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import sys

from . import VERSION, applicability, discover, gates, llm, manifests, metrics, relations
from .common import git_exclude, list_files, load_json, write_json

TOOL_DIR = Path(__file__).resolve().parent.parent
GUIDES_ROOT = TOOL_DIR.parent.parent


def scan_one(path, root, root_url, cfg, now, use_scc):
    files = list_files(path)
    facts = manifests.parse_repo(path, files)
    gfacts = discover.git_facts(path, now, cfg['activity']['window_days'])
    ident = discover.identity(path, root, root_url, gfacts['remote_key'])
    m = metrics.count(path, files, use_scc)
    has_ci = bool(facts['gitlab_ci'] or facts['github'])
    rel_parts = path.relative_to(root).parts if path != root else (path.name,)
    cls, reasons = discover.classify(rel_parts, path.name, gfacts, has_ci, m['code_lines'] + m['config_lines'],
                                     cfg['activity'], doc_lines=m['doc_lines'], doc_files=m['doc_files'])
    py = facts['pyproject'] or {}
    record = {
        'id': ident['url'],
        'name': path.name,
        'group_path': '/'.join(rel_parts),
        'url_key': ident['key'],
        'url_source': ident['source'],
        'url_verified': bool(ident['key'] and gfacts['remote_key'] and ident['key'] == gfacts['remote_key']),
        'local_path': str(path),
        'git': gfacts,
        'activity': {'class': cls, 'reasons': reasons, 'has_ci': has_ci},
        'metrics': m,
        'top_level': sorted({f.split('/')[0] + ('/' if '/' in f else '') for f in files})[:80],
        'agents': {'agents_md': 'AGENTS.md' in files, 'claude_md': 'CLAUDE.md' in files,
                   'agent_dir': any(f.startswith('.agent/') for f in files),
                   'gate_json': '.agent/gate.json' in files},
        'makefile': {'targets': sorted(facts['makefile']['targets']),
                     'name_vars': {k: v['value'] for k, v in facts['makefile']['name_vars'].items()},
                     'includes': facts['makefile']['includes']},
        'ci': {'gitlab': ({'path': facts['gitlab_ci']['path'], 'stages': facts['gitlab_ci']['stages'],
                           'jobs': [{'name': j['name'], 'stage': j['stage'], 'line': j['line']}
                                    for j in facts['gitlab_ci']['jobs']],
                           'includes': facts['gitlab_ci']['includes']} if facts['gitlab_ci'] else None),
               'github': [{'path': w['path'], 'jobs': w['jobs']} for w in facts['github']]},
        'manifests': {
            'pyproject': ({'path': py.get('path'), 'name': py.get('name'), 'sources': py.get('sources'),
                           'packages': py.get('packages'), 'error': py.get('error'),
                           'deps': [{k: v for k, v in d.items() if k != 'line'} for d in py.get('deps') or []]}
                          if py else None),
            'requirements': [{'path': r['path'], 'deps': [d['name'] for d in r['deps']], 'index_hosts': r['index_hosts']}
                             for r in facts['requirements']],
            'package_json': [{k: v for k, v in p.items() if k != 'deps'} | {'deps': [d['name'] for d in p.get('deps') or []]}
                             for p in facts['package_json'] if 'node_modules/' not in p['path']],
            'go_mod': [{'path': g['path'], 'module': g['module'], 'requires': [r['module'] for r in g['requires']]}
                       for g in facts['go_mod']],
            'dockerfiles': facts['dockerfiles'],
            'compose': facts['compose'],
            'helm': facts['helm'],
            'argocd': facts['argocd'],
            'env': facts['env'],
        },
        'publishes': {'python': [n for n in [py.get('name'), (facts['setup_name'] or {}).get('name')] if n],
                      'python_modules': facts['python_modules'],
                      'npm': [p['name'] for p in facts['package_json'] if p.get('name') and not p.get('private')
                              and 'node_modules/' not in p['path']],
                      'go': [g['module'] for g in facts['go_mod'] if g.get('module')]},
        'grpc': {'protos': facts['protos'], 'clients': facts['grpc_clients'][:20], 'servers': facts['grpc_servers'][:20]},
    }
    return record, facts, files


def cmd_scan(args):
    now = dt.datetime.fromisoformat(args.now) if args.now else dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=dt.timezone.utc)
    cfg, known = applicability.load_config(args.rules, args.guides_root)
    use_scc = shutil.which('scc') is not None and not args.no_scc
    root_urls = {}
    for item in args.root_url or []:
        if '=' not in item:
            print(f'error: --root-url expects <dir>=<url>: {item}', file=sys.stderr)
            return 2
        directory, url = item.split('=', 1)
        if not url.startswith(('https://', 'http://')):
            print(f'error: --root-url needs an http(s) URL: {url}', file=sys.stderr)
            return 2
        root_urls[Path(directory).expanduser().resolve()] = url.rstrip('/')
    roots = [Path(r).expanduser().resolve() for r in args.roots]
    roots += [r for r in root_urls if r not in roots]
    # Focus mode: report only the chosen repositories and their links, but scan context roots so the links resolve.
    focus = list(args.focus or [])
    given = [Path(r).expanduser().resolve() for r in args.roots]
    if not focus and all((r / '.git').exists() for r in given):
        focus = [str(r) for r in given]
    if focus and not args.no_context:
        for ctx in context_roots(args, roots):
            if ctx.is_dir() and not any(ctx == r or ctx.is_relative_to(r) for r in roots):
                roots = [r for r in roots if not r.is_relative_to(ctx)] + [ctx]
    # A root inside another root would be scanned twice.
    roots = [r for r in roots if not any(o != r and r.is_relative_to(o) for o in roots)]
    if focus:
        print(f'focus: {len(focus)} repositories; roots: {", ".join(str(r) for r in roots)}', file=sys.stderr)
    jobs = []
    for root in roots:
        if not root.is_dir():
            print(f'error: not a directory: {root}', file=sys.stderr)
            return 2
        for path in discover.find_repos([root]):
            jobs.append((path, root, root_urls.get(root)))
    print(f'repo-scan {VERSION}: {len(jobs)} repositories, counter={"scc" if use_scc else "builtin"}', file=sys.stderr)
    if not use_scc and not args.no_scc:
        print('hint: scc is not installed; run `make repo-scan-tools` or tools/repo-scan/check-tools.sh', file=sys.stderr)
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        scanned = list(pool.map(lambda j: scan_one(j[0], j[1], j[2], cfg, now, use_scc), jobs))
    counts = {}
    for record, _, _ in scanned:  # two checkouts of one URL keep distinct ids
        base = record['id']
        counts[base] = counts.get(base, 0) + 1
        if counts[base] > 1:
            record['id'] = f'{base}#copy{counts[base]}'
    records = []
    for record, facts, _ in scanned:
        records.append(dict(record, facts=facts))
    rel = relations.build(records, trusted_min=args.trusted_min)
    for r in records:
        r.setdefault('kafka_topics', [])
    rules_file = Path(args.rules).resolve()
    guides_root = Path(args.guides_root).resolve()
    guides = {'rules_file': (rules_file.relative_to(guides_root).as_posix()
                             if rules_file.is_relative_to(guides_root) else rules_file.name),
              'note': 'repository applicability only; per-task workflow choice stays with JEV (task_routing is a hint)',
              'guide_ids': {'workflows': sorted(g for k, g in known if k == 'workflows'),
                            'rules': sorted(g for k, g in known if k == 'rules')},
              'repositories': {}}
    for r, (_, facts, files) in zip(records, scanned):
        guides['repositories'][r['id']] = applicability.apply(cfg, known, r, facts, files, rel['edges'])
    focus_ids = []
    if focus:
        focus_ids = [r['id'] for r in match_repos(records, focus)]
        missing = [f for f in focus if not match_repos(records, [f])]
        if missing:
            print(f'error: focus repositories not found: {", ".join(missing)}', file=sys.stderr)
            return 2
        rel = focus_view(rel, set(focus_ids), args.trusted_min)
        keep = set(focus_ids) | {e['from'] for e in rel['edges']} | {e['to'] for e in rel['edges']}
        records = [dict(r, focus=r['id'] in focus_ids) for r in records if r['id'] in keep]
        guides['repositories'] = {k: v for k, v in guides['repositories'].items() if k in focus_ids}
    public = [{k: v for k, v in r.items() if k != 'facts'} for r in records]
    out = Path(args.out)
    classes = {}
    for r in public:
        classes[r['activity']['class']] = classes.get(r['activity']['class'], 0) + 1
    meta = {'version': VERSION, 'generated_at': now.isoformat(),
            'roots': [{'url': root_urls.get(r) or (discover.expected_url(r / '_', r)[1] or '')[:-2] or None,
                       'source': 'root-url' if r in root_urls else 'path'} for r in roots],
            'tools': {'counter': 'scc' if use_scc else 'builtin', 'semgrep': shutil.which('semgrep') is not None},
            'counts': {'repositories': len(public), 'by_class': classes}}
    if focus_ids:
        meta['focus'] = focus_ids
    # Local paths appear only here (llm and gate stages need them), never as identity.
    write_json(out / 'repositories.json', dict(meta, root_paths=[str(r) for r in roots], repositories=public))
    write_json(out / 'relationships.json', dict(meta, **rel))
    write_json(out / 'guide-applicability.json', dict(meta, **guides))
    (out / 'graph.mmd').write_text(mermaid(public, rel['edges']))
    if args.write_repo_artifacts:
        for r in public:
            if focus_ids and r['id'] not in focus_ids:
                continue
            write_repo_artifacts(r, rel, guides['repositories'][r['id']])
    print(json.dumps({'out': str(out), 'repositories': len(public), 'by_class': classes,
                      'edges_by_kind': rel['stats']['edges_by_kind'],
                      'trusted_by_kind': rel['stats']['trusted_by_kind'], 'unresolved': rel['stats']['unresolved']},
                     indent=1))
    return 0


def context_roots(args, roots):
    """Roots scanned only to resolve links of focus repositories: --context-root, then REPO_SCAN_CONTEXT_ROOTS
    (os.pathsep or space separated), then `context_roots` in ~/.config/agentic/repo-scan.json, else the top group
    directory `<host>/<group>` above each focus repository."""
    raw = list(args.context_root or [])
    if not raw and os.environ.get('REPO_SCAN_CONTEXT_ROOTS'):
        raw = os.environ['REPO_SCAN_CONTEXT_ROOTS'].replace(os.pathsep, ' ').split()
    if not raw:
        cfg = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'agentic/repo-scan.json'
        try:
            raw = json.loads(cfg.read_text()).get('context_roots', [])
        except (OSError, ValueError, AttributeError):
            raw = []
    if raw:
        return [Path(r).expanduser().resolve() for r in raw]
    found = []
    for root in roots:
        parts = root.parts
        hosts = [i for i, part in enumerate(parts[:-1]) if discover.DOMAIN.match(part)]
        if hosts and hosts[-1] + 2 <= len(parts):
            top = Path(*parts[:hosts[-1] + 2])
            if top not in found:
                found.append(top)
    return found


def focus_view(rel, focus_ids, trusted_min):
    """Edges and unresolved links that touch the focus repositories, with recomputed stats."""
    edges = [e for e in rel['edges'] if e['from'] in focus_ids or e['to'] in focus_ids]
    unresolved = [u for u in rel['unresolved'] if u['from'] in focus_ids]
    kinds, trusted, reasons = {}, {}, {}
    for e in edges:
        kinds[e['kind']] = kinds.get(e['kind'], 0) + 1
        if e['trusted']:
            trusted[e['kind']] = trusted.get(e['kind'], 0) + 1
    for u in unresolved:
        key = f'{u["kind"]}:{u["reason"]}'
        reasons[key] = reasons.get(key, 0) + 1
    stats = dict(rel['stats'], edges=len(edges), edges_by_kind=kinds, trusted_min=trusted_min,
                 trusted=sum(trusted.values()), trusted_by_kind=trusted, unresolved=len(unresolved),
                 unresolved_by_reason=reasons)
    return {'edges': edges, 'unresolved': unresolved, 'stats': stats}


def write_repo_artifacts(record, rel, guide):
    repo = Path(record['local_path'])
    target = repo / '.agentic'
    target.mkdir(exist_ok=True)
    write_json(target / 'repo-scan.json', dict({k: v for k, v in record.items() if k != 'local_path'}, guides=guide))
    write_json(target / 'dependencies.json', {
        'repo': record['id'],
        'outgoing': [e for e in rel['edges'] if e['from'] == record['id']],
        'incoming': [e for e in rel['edges'] if e['to'] == record['id']],
        'unresolved': [u for u in rel['unresolved'] if u['from'] == record['id']],
    })
    git_exclude(repo, '.agentic/')


def mermaid(records, edges):
    used = {e['from'] for e in edges} | {e['to'] for e in edges}
    ids = {r['id']: f'n{i}' for i, r in enumerate(sorted(records, key=lambda r: r['id'])) if r['id'] in used}
    lines = ['flowchart LR']
    for r in sorted(records, key=lambda r: r['id']):
        if r['id'] in ids:
            label = r['id'].split('://', 1)[-1].replace('"', "'")
            lines.append(f'  {ids[r["id"]]}["{label}"]:::{r["activity"]["class"]}')
    lines.append('  %% solid: trusted (confidence >= trusted_min); dashed: below the threshold')
    for e in edges:
        arrow = '-->' if e.get('trusted') else '-.->'
        lines.append(f'  {ids[e["from"]]} {arrow}|{e["kind"]} {e["confidence"]}| {ids[e["to"]]}')
    lines += ['  classDef active fill:#d4f4dd,stroke:#2a7a3b', '  classDef stale fill:#fff4cc,stroke:#a07800',
              '  classDef docs fill:#dbe9ff,stroke:#2f5fa8',
              '  classDef archived fill:#e6e6e6,stroke:#777', '  classDef junk fill:#f8d7da,stroke:#a33']
    return '\n'.join(lines) + '\n'


def scan_records(scan_dir):
    return load_json(Path(scan_dir) / 'repositories.json')['repositories']


def match_repos(records, wanted):
    """Records for a GitLab URL (with or without https://), the old 'host/path' or short form, a path suffix
    (`example-group/order-service`), a repository name, or a local path."""
    out = []
    for w in wanted:
        key = w.split('://', 1)[-1].strip('/').lower()
        local = str(Path(w).expanduser().resolve()) if not w.startswith(('http://', 'https://')) else None
        for r in records:
            rid = r['id'].split('://', 1)[-1].lower()
            if (rid == key or rid.endswith('/' + key) or r['name'] == w or r.get('local_path') == local) \
                    and r not in out:
                out.append(r)
    return out


def resolve_targets(args):
    """(id, local path) pairs for gate commands: plain directories, or ids looked up in --in."""
    targets, records = [], None
    for w in args.repos:
        path = Path(w).expanduser()
        if path.is_dir() and (path / '.git').exists():
            path = path.resolve()
            remote = discover.git_facts(path, dt.datetime.now(dt.timezone.utc), 1)['remote_key']
            targets.append((discover.identity(path, path.parent, None, remote)['url'], str(path)))
            continue
        if records is None:
            records = scan_records(args.scan_dir) if args.scan_dir else []
        found = match_repos(records, [w])
        if len(found) != 1:
            raise SystemExit(f'error: {w!r} matches {len(found)} repositories'
                             + ('' if args.scan_dir else ' (pass --in SCAN_DIR to look up URLs)'))
        targets.append((found[0]['id'], found[0]['local_path']))
    return targets


def cmd_gate_propose(args):
    if args.repos:
        targets = resolve_targets(args)
    else:
        targets = [(r['id'], r['local_path']) for r in scan_records(args.scan_dir or '.')
                   if r['activity']['class'] in args.classes.split(',')]
    proposals = {}
    for rid, path in targets:
        proposals[rid] = gates.propose_for(path)
    out = Path(args.out or args.scan_dir or '.')
    write_json(out / 'gate-proposals.json', {'note': 'candidates only; nothing was executed', 'proposals': proposals})
    with_cmds = sum(1 for p in proposals.values() if p['gate']['commands'])
    print(f'{len(proposals)} proposals, {with_cmds} with commands -> {out / "gate-proposals.json"}')
    return 0


def cmd_gate_verify(args):
    reports = []
    for rid, local in resolve_targets(args):
        path = Path(local)
        if not (path / '.git').exists():
            print(f'error: not a git repository: {path}', file=sys.stderr)
            return 2
        report = dict(gates.verify(path, timeout=args.timeout, write=not args.no_write, force=args.force), repo=rid)
        reports.append(report)
        for res in report['results']:
            print(f'{res["exit"]:>4} {res["seconds"]:>6}s  {path.name}: {res["command"]}')
        print(f'  gate: {json.dumps(report["gate"])} written={report["written"]} {report.get("skipped", "")}')
    if args.out:
        write_json(Path(args.out) / 'gate-verify.json', {'reports': reports})
    return 0


def cmd_llm(args):
    model = args.model or (os.environ.get('AGENTIC_LLM_MODEL') or llm.DEFAULT_LITELLM_MODEL
                           if args.provider == 'litellm' else 'haiku')
    if args.provider == 'litellm':
        model = llm.bare_model_id(model)
    if args.provider == 'claude' and model not in llm.CLAUDE_MODELS:
        print(f'error: claude model must be one of {", ".join(llm.CLAUDE_MODELS)}', file=sys.stderr)
        return 2

    def select(repos):
        if args.repo:
            chosen = match_repos(repos, args.repo)
        else:
            chosen = [r for r in repos if r['activity']['class'] in args.classes.split(',')]
        return chosen[:args.limit] if args.limit else chosen

    result = llm.assess(args.scan_dir, args.provider, model, select, args.out or args.scan_dir,
                        timeout=args.timeout, use_cache=not args.no_cache,
                        log=lambda m: print(m, file=sys.stderr))
    ok = sum(1 for a in result['assessments'].values() if a.get('status') == 'ok')
    print(f'{ok}/{len(result["assessments"])} assessments ok -> {Path(args.out or args.scan_dir) / "llm-assessment.json"}')
    return 0 if ok else 1


def add_scan_args(s):
    s.add_argument('roots', nargs='+', help='group directories or single repositories')
    s.add_argument('--out', required=True)
    s.add_argument('--root-url', action='append', metavar='DIR=URL',
                   help='GitLab URL of a root (repeatable), e.g. ~/work/gitlab.example.com/group=https://gitlab.example.com/group; '
                        'default: inferred from the path')
    s.add_argument('--trusted-min', type=float, default=0.8, help='confidence for trusted edges (default 0.8)')
    s.add_argument('--rules', default=str(TOOL_DIR / 'applicability.json'))
    s.add_argument('--guides-root', default=str(GUIDES_ROOT))
    s.add_argument('--now', help='reference time (ISO 8601) for the activity window')
    s.add_argument('--jobs', type=int, default=8)
    s.add_argument('--no-scc', action='store_true', help='use the built-in counter even when scc is on PATH')
    s.add_argument('--focus', action='append', metavar='REPO',
                   help='report only this repository and its links (repeatable; path, URL or short form); '
                        'roots that are repositories themselves are the focus by default')
    s.add_argument('--context-root', action='append', metavar='DIR',
                   help='extra root scanned only to resolve focus links (repeatable; default: REPO_SCAN_CONTEXT_ROOTS, '
                        '~/.config/agentic/repo-scan.json, else the <host>/<group> directory above the focus)')
    s.add_argument('--no-context', action='store_true', help='focus mode without context roots')
    s.add_argument('--write-repo-artifacts', action='store_true',
                   help='write .agentic/repo-scan.json and .agentic/dependencies.json into each repository')


def add_llm_args(m):
    m.add_argument('--provider', choices=sorted(llm.PROVIDERS), default='claude')
    m.add_argument('--model')
    m.add_argument('--repo', action='append', help='GitLab URL, host/path, path suffix, name or local path; repeatable')
    m.add_argument('--classes', default='active')
    m.add_argument('--limit', type=int, default=0)
    m.add_argument('--timeout', type=int, default=300)
    m.add_argument('--no-cache', action='store_true')


def cmd_run(args):
    code = cmd_scan(args)
    if code or args.skip_llm:
        return code
    stage2 = argparse.Namespace(**vars(args))
    stage2.scan_dir, stage2.out = args.out, None
    if not args.repo:  # focus repositories are assessed whatever their class
        stage2.repo = list(args.focus or []) or \
            [r for r in args.roots if (Path(r).expanduser() / '.git').exists()] or None
    return cmd_llm(stage2)


def main(argv=None):
    p = argparse.ArgumentParser(prog='repo_scan.py', description='Offline analysis of many Git repositories.')
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('scan', help='stage 1: static scan (no network, no repository code runs)')
    add_scan_args(s)
    s.set_defaults(func=cmd_scan)
    r = sub.add_parser('run', help='stage 1 + stage 2: scan, then the LLM assessment of the selected repositories')
    add_scan_args(r)
    add_llm_args(r)
    r.add_argument('--skip-llm', action='store_true', help='stage 1 only')
    r.set_defaults(func=cmd_run)
    g = sub.add_parser('gate-propose', help='candidate .agent/gate.json from Makefile and CI (nothing runs)')
    g.add_argument('repos', nargs='*', help='repository paths, or URLs / short forms looked up in --in; '
                                            'default: all repositories from --in')
    g.add_argument('--in', dest='scan_dir')
    g.add_argument('--out')
    g.add_argument('--classes', default='active,stale')
    g.set_defaults(func=cmd_gate_propose)
    v = sub.add_parser('gate-verify', help='RUNS candidate checks in the named repositories; writes .agent/gate.json')
    v.add_argument('repos', nargs='+', help='repository paths, or URLs / short forms looked up in --in')
    v.add_argument('--in', dest='scan_dir')
    v.add_argument('--timeout', type=int, default=600)
    v.add_argument('--no-write', action='store_true')
    v.add_argument('--force', action='store_true', help='overwrite a tracked .agent/gate.json in the working copy')
    v.add_argument('--out')
    v.set_defaults(func=cmd_gate_verify)
    m = sub.add_parser('llm', help='stage 2: LLM assessment over stage-1 output')
    m.add_argument('--in', dest='scan_dir', required=True)
    m.add_argument('--out')
    add_llm_args(m)
    m.set_defaults(func=cmd_llm)
    args = p.parse_args(argv)
    return args.func(args)
