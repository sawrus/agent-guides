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


def scan_one(path, root, cfg, now, use_scc):
    files = list_files(path)
    facts = manifests.parse_repo(path, files)
    gfacts = discover.git_facts(path, now, cfg['activity']['window_days'])
    remote_host = (gfacts['remote_key'] or '').split('/')[0] or None
    url_key, url_expected = discover.expected_url(path, root, remote_host)
    m = metrics.count(path, files, use_scc)
    has_ci = bool(facts['gitlab_ci'] or facts['github'])
    rel_parts = path.relative_to(root).parts if path != root else (path.name,)
    cls, reasons = discover.classify(rel_parts, path.name, gfacts, has_ci, m['code_lines'] + m['config_lines'],
                                     cfg['activity'])
    rid = url_key or gfacts['remote_key'] or str(path)
    py = facts['pyproject'] or {}
    record = {
        'id': rid,
        'name': path.name,
        'path': str(path),
        'group_path': '/'.join(rel_parts),
        'url_key': url_key,
        'url_expected': url_expected,
        'url_verified': bool(url_key and gfacts['remote_key'] and url_key == gfacts['remote_key']),
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
    jobs = []
    for root in args.roots:
        root = Path(root).expanduser().resolve()
        if not root.is_dir():
            print(f'error: not a directory: {root}', file=sys.stderr)
            return 2
        for path in discover.find_repos([root]):
            jobs.append((path, root))
    print(f'repo-scan {VERSION}: {len(jobs)} repositories, counter={"scc" if use_scc else "builtin"}', file=sys.stderr)
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        scanned = list(pool.map(lambda j: scan_one(j[0], j[1], cfg, now, use_scc), jobs))
    seen = {}
    for record, _, _ in scanned:  # two checkouts of one remote keep distinct ids
        if record['id'] in seen:
            record['id'] = f'{record["id"]}#{record["path"]}'
        seen[record['id']] = True
    records = []
    for record, facts, _ in scanned:
        records.append(dict(record, facts=facts))
    rel = relations.build(records)
    for r in records:
        r.setdefault('kafka_topics', [])
    guides = {'guides_root': str(Path(args.guides_root).resolve()), 'rules_file': str(Path(args.rules).resolve()),
              'note': 'repository applicability only; per-task workflow choice stays with JEV (task_routing is a hint)',
              'guide_ids': {'workflows': sorted(g for k, g in known if k == 'workflows'),
                            'rules': sorted(g for k, g in known if k == 'rules')},
              'repositories': {}}
    for r, (_, facts, files) in zip(records, scanned):
        guides['repositories'][r['id']] = applicability.apply(cfg, known, r, facts, files, rel['edges'])
    public = [{k: v for k, v in r.items() if k != 'facts'} for r in records]
    out = Path(args.out)
    classes = {}
    for r in public:
        classes[r['activity']['class']] = classes.get(r['activity']['class'], 0) + 1
    meta = {'version': VERSION, 'generated_at': now.isoformat(), 'roots': [str(Path(r).resolve()) for r in args.roots],
            'tools': {'counter': 'scc' if use_scc else 'builtin', 'semgrep': shutil.which('semgrep') is not None},
            'counts': {'repositories': len(public), 'by_class': classes}}
    write_json(out / 'repositories.json', dict(meta, repositories=public))
    write_json(out / 'relationships.json', dict(meta, **rel))
    write_json(out / 'guide-applicability.json', dict(meta, **guides))
    (out / 'graph.mmd').write_text(mermaid(public, rel['edges']))
    if args.write_repo_artifacts:
        for r in public:
            write_repo_artifacts(r, rel, guides['repositories'][r['id']])
    print(json.dumps({'out': str(out), 'repositories': len(public), 'by_class': classes,
                      'edges_by_kind': rel['stats']['edges_by_kind'], 'unresolved': rel['stats']['unresolved']},
                     indent=1))
    return 0


def write_repo_artifacts(record, rel, guide):
    repo = Path(record['path'])
    target = repo / '.agentic'
    target.mkdir(exist_ok=True)
    write_json(target / 'repo-scan.json', dict(record, guides=guide))
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
            host = (r.get('url_key') or '').split('.')[0]
            label = (f'{host}: ' if host else '') + r['group_path'].replace('"', "'")
            lines.append(f'  {ids[r["id"]]}["{label}"]:::{r["activity"]["class"]}')
    for e in edges:
        lines.append(f'  {ids[e["from"]]} -->|{e["kind"]} {e["confidence"]}| {ids[e["to"]]}')
    lines += ['  classDef active fill:#d4f4dd,stroke:#2a7a3b', '  classDef stale fill:#fff4cc,stroke:#a07800',
              '  classDef archived fill:#e6e6e6,stroke:#777', '  classDef junk fill:#f8d7da,stroke:#a33']
    return '\n'.join(lines) + '\n'


def scan_records(scan_dir):
    return load_json(Path(scan_dir) / 'repositories.json')['repositories']


def cmd_gate_propose(args):
    if args.repos:
        targets = [(str(Path(p).resolve()), str(Path(p).resolve())) for p in args.repos]
    else:
        targets = [(r['id'], r['path']) for r in scan_records(args.scan_dir)
                   if r['activity']['class'] in args.classes.split(',')]
    proposals = {}
    for rid, path in targets:
        proposals[rid] = dict(gates.propose_for(path), path=path)
    out = Path(args.out or args.scan_dir)
    write_json(out / 'gate-proposals.json', {'note': 'candidates only; nothing was executed', 'proposals': proposals})
    with_cmds = sum(1 for p in proposals.values() if p['gate']['commands'])
    print(f'{len(proposals)} proposals, {with_cmds} with commands -> {out / "gate-proposals.json"}')
    return 0


def cmd_gate_verify(args):
    reports = []
    for repo in args.repos:
        path = Path(repo).expanduser().resolve()
        if not (path / '.git').exists():
            print(f'error: not a git repository: {path}', file=sys.stderr)
            return 2
        report = gates.verify(path, timeout=args.timeout, write=not args.no_write, force=args.force)
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
    if args.provider == 'litellm' and model.startswith('dats_ai/'):
        model = model.split('/', 1)[1]  # OpenCode provider prefix; the proxy wants the bare id
    if args.provider == 'claude' and model not in llm.CLAUDE_MODELS:
        print(f'error: claude model must be one of {", ".join(llm.CLAUDE_MODELS)}', file=sys.stderr)
        return 2

    def select(repos):
        if args.repo:
            wanted = set(args.repo)
            chosen = [r for r in repos if r['id'] in wanted or r['name'] in wanted or r['group_path'] in wanted
                      or r['path'] in wanted]
        else:
            chosen = [r for r in repos if r['activity']['class'] in args.classes.split(',')]
        return chosen[:args.limit] if args.limit else chosen

    result = llm.assess(args.scan_dir, args.provider, model, select, args.out or args.scan_dir,
                        timeout=args.timeout, use_cache=not args.no_cache,
                        log=lambda m: print(m, file=sys.stderr))
    ok = sum(1 for a in result['assessments'].values() if a.get('status') == 'ok')
    print(f'{ok}/{len(result["assessments"])} assessments ok -> {Path(args.out or args.scan_dir) / "llm-assessment.json"}')
    return 0 if ok else 1


def main(argv=None):
    p = argparse.ArgumentParser(prog='repo_scan.py', description='Offline analysis of many Git repositories.')
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('scan', help='stage 1: static scan (no network, no repository code runs)')
    s.add_argument('roots', nargs='+')
    s.add_argument('--out', required=True)
    s.add_argument('--rules', default=str(TOOL_DIR / 'applicability.json'))
    s.add_argument('--guides-root', default=str(GUIDES_ROOT))
    s.add_argument('--now', help='reference time (ISO 8601) for the activity window')
    s.add_argument('--jobs', type=int, default=8)
    s.add_argument('--no-scc', action='store_true', help='use the built-in counter even when scc is on PATH')
    s.add_argument('--write-repo-artifacts', action='store_true',
                   help='write .agentic/repo-scan.json and .agentic/dependencies.json into each repository')
    s.set_defaults(func=cmd_scan)
    g = sub.add_parser('gate-propose', help='candidate .agent/gate.json from Makefile and CI (nothing runs)')
    g.add_argument('repos', nargs='*', help='repository paths; default: repositories from --in')
    g.add_argument('--in', dest='scan_dir', default='.')
    g.add_argument('--out')
    g.add_argument('--classes', default='active,stale')
    g.set_defaults(func=cmd_gate_propose)
    v = sub.add_parser('gate-verify', help='RUNS candidate checks in the named repositories; writes .agent/gate.json')
    v.add_argument('repos', nargs='+')
    v.add_argument('--timeout', type=int, default=600)
    v.add_argument('--no-write', action='store_true')
    v.add_argument('--force', action='store_true', help='overwrite a tracked .agent/gate.json in the working copy')
    v.add_argument('--out')
    v.set_defaults(func=cmd_gate_verify)
    m = sub.add_parser('llm', help='stage 2: LLM assessment over stage-1 output')
    m.add_argument('--in', dest='scan_dir', required=True)
    m.add_argument('--out')
    m.add_argument('--provider', choices=sorted(llm.PROVIDERS), default='claude')
    m.add_argument('--model')
    m.add_argument('--repo', action='append', help='id, name, group path or path; repeatable')
    m.add_argument('--classes', default='active')
    m.add_argument('--limit', type=int, default=0)
    m.add_argument('--timeout', type=int, default=300)
    m.add_argument('--no-cache', action='store_true')
    m.set_defaults(func=cmd_llm)
    args = p.parse_args(argv)
    return args.func(args)
