"""Declarative guide applicability (tools/repo-scan/applicability.json).

Repository applicability (rules and workflows that fit the repository) is separate from task routing
(candidate workflows per task kind, ordered). The real per-task choice stays with JEV.
"""
from fnmatch import fnmatch
from pathlib import Path
import re

from .common import load_json
from .manifests import all_deps


def guide_paths(guides_root):
    """id -> (kind, path) for every workflow and rule under areas/."""
    root = Path(guides_root)
    out = {}
    for kind in ('workflows', 'rules'):
        for path in sorted((root / 'areas').glob(f'**/{kind}/*.md')):
            rel = path.relative_to(root / 'areas')
            gid = '/'.join(rel.parts[:-2] + (path.stem,))
            out[(kind, gid)] = path.relative_to(root).as_posix()
    return out


def load_config(path, guides_root):
    cfg = load_json(path)
    known = guide_paths(guides_root)
    errors = []
    for rule in cfg['repo_rules']:
        for kind in ('workflows', 'rules'):
            for gid in rule.get(kind, []):
                if (kind, gid) not in known:
                    errors.append(f'{rule["id"]}: unknown {kind[:-1]} id {gid}')
    for task, ids in cfg['task_routing'].items():
        for gid in ids:
            if ('workflows', gid) not in known:
                errors.append(f'task_routing.{task}: unknown workflow id {gid}')
    if errors:
        raise ValueError('applicability.json: ' + '; '.join(errors))
    return cfg, known


def manifest_kinds(facts, files):
    kinds = {}
    if (facts.get('makefile') or {}).get('targets'):
        first = next(iter(facts['makefile']['targets'].values()))
        kinds['makefile'] = first['path']
    if facts.get('gitlab_ci'):
        kinds['gitlab-ci'] = facts['gitlab_ci']['path']
    if facts.get('github'):
        kinds['github-actions'] = facts['github'][0]['path']
    for key, field in (('docker-compose', 'compose'), ('dockerfile', 'dockerfiles'), ('helm', 'helm'),
                       ('argocd', 'argocd'), ('proto', 'protos'), ('package-json', 'package_json'),
                       ('go-mod', 'go_mod'), ('requirements', 'requirements')):
        if facts.get(field):
            kinds[key] = facts[field][0]['path']
    if facts.get('pyproject'):
        kinds['pyproject'] = facts['pyproject']['path']
    envs = [e for e in facts.get('env') or [] if e['keys'] and not e['path'].endswith(('.yml', '.yaml'))]
    if envs:
        kinds['env'] = envs[0]['path']
    return kinds


class Context:
    def __init__(self, record, facts, files, edges):
        self.record, self.facts, self.files = record, facts, files
        self.kinds = manifest_kinds(facts, files)
        self.deps = all_deps(facts)
        self.edges = edges


def evaluate(cond, ctx):
    """Return (matched, evidence list)."""
    if 'all' in cond:
        evidence = []
        for sub in cond['all']:
            ok, e = evaluate(sub, ctx)
            if not ok:
                return False, []
            evidence += e
        return True, evidence
    if 'any' in cond:
        evidence, matched = [], False
        for sub in cond['any']:
            ok, e = evaluate(sub, ctx)
            if ok:
                matched, evidence = True, evidence + e
        return matched, evidence
    if 'not' in cond:
        ok, _ = evaluate(cond['not'], ctx)
        return (not ok), []
    if 'code_lines' in cond:
        n = ctx.record['metrics']['code_lines']
        return n >= cond['code_lines'], [{'path': '.', 'key': f'code_lines={n}'}]
    if 'language' in cond:
        lang = ctx.record['metrics']['languages'].get(cond['language'], {})
        n = lang.get('code', 0)
        return n >= cond.get('min_lines', 1), [{'path': '.', 'key': f'language:{cond["language"]}={n}'}]
    if 'manifest' in cond:
        path = ctx.kinds.get(cond['manifest'])
        return bool(path), [{'path': path, 'key': cond['manifest']}] if path else []
    if 'dependency' in cond:
        pattern = re.compile(f'^(?:{cond["dependency"]})$', re.I)
        hits = [d for d in ctx.deps if pattern.match(d['name'])]
        return bool(hits), [{'path': d['path'], 'line': d.get('line'), 'key': d['name']} for d in hits[:3]]
    if 'file' in cond:
        hit = next((f for f in ctx.files if fnmatch(f, cond['file'])), None)
        return bool(hit), [{'path': hit, 'key': f'file:{cond["file"]}'}] if hit else []
    if 'make_target' in cond:
        t = (ctx.facts.get('makefile') or {}).get('targets', {}).get(cond['make_target'])
        return bool(t), [{'path': t['path'], 'line': t['line'], 'key': f'target:{cond["make_target"]}'}] if t else []
    if 'activity' in cond:
        cls = ctx.record['activity']['class']
        return cls in cond['activity'], [{'path': '.', 'key': f'activity={cls}'}]
    if 'agents' in cond:
        ok = bool(ctx.record['agents'].get(cond['agents']))
        return ok, [{'path': 'AGENTS.md' if cond['agents'] == 'agents_md' else '.agent/', 'key': cond['agents']}] if ok else []
    if 'relationship' in cond:
        rid, direction = ctx.record['id'], cond.get('direction', 'any')
        hits = [e for e in ctx.edges if e['kind'] == cond['relationship'] and (
            (direction in ('out', 'any') and e['from'] == rid) or (direction in ('in', 'any') and e['to'] == rid))]
        return bool(hits), [{'path': e['evidence'][0]['path'], 'line': e['evidence'][0].get('line'),
                             'key': f'{e["kind"]}: {e["from"]} -> {e["to"]}'} for e in hits[:3]]
    raise ValueError(f'unknown condition: {cond}')


def apply(cfg, known, record, facts, files, edges):
    cls = record['activity']['class']
    if cls not in cfg['guidance_classes']:
        return {'class': cls, 'rules': [], 'workflows': [], 'task_routing': {}, 'note': f'no guidance for class {cls}'}
    result = {'class': cls, 'rules': {}, 'workflows': {}, 'task_routing': {}}
    ctx = Context(record, facts, files, edges)
    for rule in cfg['repo_rules']:
        ok, evidence = evaluate(rule['when'], ctx)
        if not ok:
            continue
        evidence = [{k: v for k, v in e.items() if v is not None} for e in evidence]
        for kind in ('rules', 'workflows'):
            for gid in rule.get(kind, []):
                entry = result[kind].setdefault(gid, {'id': gid, 'path': known[(kind, gid)], 'confidence': 0,
                                                      'because': [], 'evidence': []})
                entry['confidence'] = max(entry['confidence'], rule.get('confidence', 0.5))
                entry['because'].append(rule['id'])
                entry['evidence'].extend(e for e in evidence if e not in entry['evidence'])
    for kind in ('rules', 'workflows'):
        result[kind] = sorted(result[kind].values(), key=lambda e: (-e['confidence'], e['id']))
    applicable = {w['id'] for w in result['workflows']}
    for task, ids in cfg['task_routing'].items():
        picks = [gid for gid in ids if gid in applicable]
        if picks:
            result['task_routing'][task] = picks
    return result
