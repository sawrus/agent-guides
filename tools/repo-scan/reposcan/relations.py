"""Cross-repository relationships with evidence. Ambiguous or unknown targets go to `unresolved`."""
import ipaddress
import re

from .common import norm_pkg, remote_key
from .manifests import ENDPOINT_KEY, TOPIC_KEY, TOPIC_KEY_SKIP, all_deps, role_from

GENERIC_NAMES = {'src', 'app', 'apps', 'api', 'main', 'project', 'service', 'services', 'backend', 'frontend', 'web',
                 'server', 'client', 'core', 'common', 'lib', 'libs', 'utils', 'util', 'test', 'tests', 'demo',
                 'scripts', 'tools', 'config', 'settings', 'docs', 'migrations', 'alembic', 'root', 'package',
                 'my-app', 'example', 'template', 'templates', 'worker', 'workers', 'gitlab-profile'}
ENV_PREFIXES = {'DEV', 'PROD', 'PRODUCTION', 'STAGE', 'STAGING', 'TEST', 'LOCAL', 'QA', 'UAT', 'PREPROD', 'DEMO'}
KEY_SUFFIXES = {'ENDPOINT', 'ENDPOINTS', 'URL', 'URLS', 'URI', 'BASE'}
INFRA = re.compile(r'(^|[_.-])(DATABASE|DB|POSTGRES|POSTGRESQL|PG|MYSQL|REDIS|KAFKA|SENTRY|S3|MINIO|ELASTIC|'
                   r'ELASTICSEARCH|ES|CLICKHOUSE|CH|VAULT|JAEGER|OTEL|OTLP|PROMETHEUS|GRAFANA|LOKI|MONGO|MONGODB|'
                   r'RABBIT|RABBITMQ|AMQP|CELERY|BROKER|SMTP|LDAP|REGISTRY|DOCKER|PYPI|NEXUS|GITLAB|GITHUB|JIRA|'
                   r'CONFLUENCE|SLACK|TELEGRAM|SCHEMA_REGISTRY|AWS|GCP|AZURE|KIBANA|LOGSTASH|SUPERSET|'
                   r'KEYCLOAK|HARBOR|ARGOCD|CONSUL|ETCD|ZOOKEEPER|NATS|MEMCACHED|SPLUNK|DATADOG|NEWRELIC)([_.-]|$)', re.I)
PUBLIC_INDEX_HOSTS = {'pypi.org', 'files.pythonhosted.org', 'registry.npmjs.org', None}


class Graph:
    def __init__(self, records):
        self.records = {r['id']: r for r in records}
        self.edges = {}
        self.unresolved = []
        self.stats = {'skipped_infra_endpoints': 0, 'external_urls': 0}

    def add(self, src, dst, kind, confidence, evidence, detail=None):
        key = (src, dst, kind)
        edge = self.edges.get(key)
        if edge is None:
            edge = self.edges[key] = {'from': src, 'to': dst, 'kind': kind, 'confidence': confidence,
                                      'detail': {}, 'evidence': []}
        edge['confidence'] = max(edge['confidence'], confidence)
        for ev in evidence:
            if ev not in edge['evidence']:
                edge['evidence'].append(ev)
        for k, v in (detail or {}).items():
            if isinstance(v, list):
                edge['detail'].setdefault(k, [])
                edge['detail'][k].extend(x for x in v if x not in edge['detail'][k])
            else:
                edge['detail'].setdefault(k, v)

    def miss(self, src, kind, ref, reason, evidence, candidates=None):
        entry = {'from': src, 'kind': kind, 'ref': ref, 'reason': reason, 'evidence': evidence}
        if candidates:
            entry['candidates'] = sorted(candidates)
        self.unresolved.append(entry)

    def choose(self, candidates):
        """One target, or None when ambiguous. Archived and junk copies lose to a single live repository."""
        candidates = sorted(set(candidates))
        if len(candidates) == 1:
            return candidates[0]
        live = [c for c in candidates if self.records[c]['activity']['class'] in ('active', 'stale')]
        return live[0] if len(live) == 1 else None

    def result(self):
        edges = sorted(self.edges.values(), key=lambda e: (e['kind'], e['from'], e['to']))
        for edge in edges:
            edge['confidence'] = round(edge['confidence'], 2)
        kinds = {}
        for edge in edges:
            kinds[edge['kind']] = kinds.get(edge['kind'], 0) + 1
        ureasons = {}
        for u in self.unresolved:
            ureasons[f'{u["kind"]}:{u["reason"]}'] = ureasons.get(f'{u["kind"]}:{u["reason"]}', 0) + 1
        stats = dict(self.stats, edges=len(edges), edges_by_kind=kinds, unresolved=len(self.unresolved),
                     unresolved_by_reason=ureasons)
        return {'edges': edges, 'unresolved': self.unresolved, 'stats': stats}


def ev(repo, path, line=None, key=None, note=None):
    out = {'repo': repo, 'path': path}
    if line is not None:
        out['line'] = line
    if key is not None:
        out['key'] = key
    if note:
        out['note'] = note
    return out


def build(records):
    """records: repository records with `facts` (manifests.parse_repo output) attached."""
    g = Graph(records)
    url_index = {}
    for r in records:
        for k in (r.get('url_key'), r['git'].get('remote_key')):
            if k:
                url_index.setdefault(k, set()).add(r['id'])
    libraries(g, records)
    http(g, records)
    kafka(g, records)
    grpc(g, records)
    ci_and_deploy(g, records, url_index)
    return g.result()


def publishers(records):
    pubs = {'python': {}, 'npm': {}}
    modules = {}
    for r in records:
        f = r['facts']
        names = []
        py = f.get('pyproject') or {}
        if py.get('name'):
            names.append(('python', py['name'], ev(r['id'], py['path'], py.get('name_line'), note='package name')))
        if f.get('setup_name'):
            s = f['setup_name']
            names.append(('python', s['name'], ev(r['id'], s['path'], s.get('line'), note='package name')))
        for pj in f.get('package_json') or []:
            if pj.get('name') and not pj.get('private') and '/node_modules/' not in pj['path']:
                names.append(('npm', pj['name'], ev(r['id'], pj['path'], pj.get('name_line'), note='package name')))
        py_names = set()
        for eco, name, evidence in names:
            key = norm_pkg(name)
            if key in GENERIC_NAMES:
                continue
            pubs[eco].setdefault(key, {}).setdefault(r['id'], evidence)
            if eco == 'python':
                py_names.add(key)
        # Only modules that carry the package name (apiutil/, wf_core/) or are declared in poetry packages
        # count as published; other top-level packages of a service are internal.
        declared = set(py.get('packages') or [])
        for mod in f.get('python_modules') or []:
            if py_names and (norm_pkg(mod) in py_names or mod in declared) and norm_pkg(mod) not in GENERIC_NAMES:
                modules.setdefault(mod, set()).add(r['id'])
    return pubs, modules


def libraries(g, records):
    pubs, modules = publishers(records)
    hosts = {r['url_key'].split('/')[0] for r in records if r.get('url_key')}
    go_modules = {}
    for r in records:
        for gm in r['facts'].get('go_mod') or []:
            if gm.get('module'):
                go_modules.setdefault(gm['module'].lower(), set()).add(r['id'])
        if r.get('url_key'):
            go_modules.setdefault(r['url_key'], set()).add(r['id'])
    for r in records:
        f, rid = r['facts'], r['id']
        sources = {s['name']: s for s in (f.get('pyproject') or {}).get('sources') or []}
        for d in all_deps(f):
            evidence = [ev(rid, d['path'], d.get('line'), key=d['name'])]
            if d['eco'] == 'go':
                mod = d['name'].lower()
                match = {t for k, ts in go_modules.items() if mod == k or mod.startswith(k + '/') for t in ts} - {rid}
                if match:
                    target = g.choose(match)
                    if target:
                        g.add(rid, target, 'library', 0.95, evidence, {'packages': [d['name']], 'ecosystem': 'go'})
                    else:
                        g.miss(rid, 'library', d['name'], 'ambiguous', evidence, match)
                elif mod.split('/')[0] in hosts:
                    g.miss(rid, 'library', d['name'], 'no publishing repo found', evidence)
                continue
            key = norm_pkg(d['name'])
            targets = pubs[d['eco']].get(key, {})
            match = set(targets) - {rid}
            if match:
                target = g.choose(match)
                if target:
                    g.add(rid, target, 'library', 0.85, evidence + [targets[target]],
                          {'packages': [d['name']], 'ecosystem': d['eco']})
                else:
                    g.miss(rid, 'library', d['name'], 'ambiguous', evidence, match)
                continue
            src = sources.get(d.get('source'))
            if src and src.get('host') not in PUBLIC_INDEX_HOSTS:
                g.miss(rid, 'library', d['name'], 'private source, no publishing repo found',
                       evidence + [ev(rid, (f.get('pyproject') or {}).get('path'), src.get('line'),
                                      key=f'source:{src["name"]}', note=f'host {src.get("host")}')])
        own = set(f.get('python_modules') or [])
        for mod, where in sorted((f.get('imports') or {}).items()):
            if mod in own or mod not in modules:
                continue
            match = modules[mod] - {rid}
            if not match:
                continue
            target = g.choose(match)
            evidence = [ev(rid, where['path'], where['line'], key=f'import {mod}', note=f'{where["count"]} imports')]
            if not target:
                g.miss(rid, 'library', mod, 'ambiguous import', evidence, match)
                continue
            existing = g.edges.get((rid, target, 'library'))
            g.add(rid, target, 'library', 0.95 if existing else 0.6, evidence, {'imports': [mod], 'ecosystem': 'python'})


def service_index(records):
    idx = {}

    def put(name, rid):
        key = norm_pkg(name.split('/')[-1])
        if key and key not in GENERIC_NAMES:
            idx.setdefault(key, set()).add(rid)

    for r in records:
        f, rid = r['facts'], r['id']
        put(r['name'], rid)
        if (f.get('pyproject') or {}).get('name'):
            put(f['pyproject']['name'], rid)
        for pj in f.get('package_json') or []:
            if pj.get('name') and '/node_modules/' not in pj['path']:
                put(pj['name'], rid)
        for var in (f.get('makefile') or {}).get('name_vars', {}).values():
            put(var['value'], rid)
        charts = [c for c in f.get('helm') or [] if c.get('name')]
        if len(charts) == 1:  # a repository with many charts is a deployment catalog, not one service
            put(charts[0]['name'], rid)
    return idx


def key_service(key):
    tokens = [t for t in key.upper().split('_') if t]
    while tokens and tokens[0] in ENV_PREFIXES:
        tokens.pop(0)
    while tokens and tokens[-1] in KEY_SUFFIXES:
        tokens.pop()
    return '-'.join(tokens).lower() if tokens else None


def host_label(host):
    try:
        ipaddress.ip_address(host)
        return None
    except ValueError:
        pass
    label = host.split('.')[0]
    return None if label in ('localhost', 'www', '') else label


def http(g, records):
    idx = service_index(records)
    for r in records:
        f, rid = r['facts'], r['id']
        groups = {}
        for env in f.get('env') or []:
            for k in env['keys']:
                if ENDPOINT_KEY.search(k['key'].upper()):
                    svc = key_service(k['key'])
                    groups.setdefault(svc, []).append((ev(rid, env['path'], k['line'], key=k['key']), k.get('host')))
        for k in f.get('code_keys') or []:
            if ENDPOINT_KEY.search(k['key']):
                groups.setdefault(key_service(k['key']), []).append((ev(rid, k['path'], k['line'], key=k['key']), None))
        for svc, items in sorted(groups.items(), key=lambda kv: kv[0] or ''):
            evidence = [e for e, _ in items]
            hosts = sorted({h for _, h in items if h})
            key_t = idx.get(norm_pkg(svc), set()) if svc else set()
            host_t = set()
            for h in hosts:
                label = host_label(h)
                if label:
                    host_t |= idx.get(norm_pkg(label), set())
            if rid in key_t and not (host_t - {rid}):
                continue  # the service describes its own URL
            key_t, host_t = key_t - {rid}, host_t - {rid}
            both = key_t & host_t
            if both:
                cands, conf, how = both, 0.9, 'key and host'
            elif host_t:
                cands, conf, how = host_t, 0.75, 'host'
            elif key_t:
                cands, conf, how = key_t, 0.7, 'key'
            else:
                if (svc and INFRA.search(svc.upper().replace('-', '_'))) or any(INFRA.search(h.split('.')[0]) for h in hosts):
                    g.stats['skipped_infra_endpoints'] += 1
                    continue
                g.miss(rid, 'http', svc or evidence[0].get('key'), 'no matching repo',
                       [dict(e, **({'hosts': hosts} if hosts and i == 0 else {})) for i, e in enumerate(evidence)])
                continue
            target = g.choose(cands)
            if target:
                g.add(rid, target, 'http', conf, evidence, {'matched_by': how, 'hosts': hosts, 'service': [svc]})
            else:
                g.miss(rid, 'http', svc, 'ambiguous', evidence, cands)


def repo_topics(r):
    f, rid = r['facts'], r['id']
    topics = {}
    for env in f.get('env') or []:
        for k in env['keys']:
            for t in k.get('topics') or []:
                if TOPIC_KEY.search(k['key'].upper()) and not TOPIC_KEY_SKIP.search(k['key'].upper()):
                    topics.setdefault(t, []).append((role_from(k['key']), ev(rid, env['path'], k['line'], key=k['key'])))
    if f.get('kafka_hint'):
        for c in f.get('kafka_code') or []:
            topics.setdefault(c['topic'], []).append((c['role'], ev(rid, c['path'], c['line'], key=c['topic'])))
    return topics


def kafka(g, records):
    by_topic = {}
    for r in records:
        for topic, items in repo_topics(r).items():
            by_topic.setdefault(topic, {})[r['id']] = items
    for r in records:
        r['kafka_topics'] = sorted(t for t, repos in by_topic.items() if r['id'] in repos)
    for topic, repos in sorted(by_topic.items()):
        if len(repos) == 1:
            rid, items = next(iter(repos.items()))
            g.miss(rid, 'kafka', topic, 'no counterpart repo', [e for _, e in items[:3]])
            continue
        roles = {rid: {role for role, _ in items} for rid, items in repos.items()}
        ids = sorted(repos)
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                evidence = [e for _, e in repos[a][:2]] + [e for _, e in repos[b][:2]]
                if 'consumer' in roles[a] and 'producer' in roles[b]:
                    g.add(a, b, 'kafka', 0.8, evidence, {'topics': [topic], 'direction': 'consumes-from'})
                elif 'consumer' in roles[b] and 'producer' in roles[a]:
                    g.add(b, a, 'kafka', 0.8, evidence, {'topics': [topic], 'direction': 'consumes-from'})
                elif 'unknown' in roles[a] or 'unknown' in roles[b]:
                    g.add(a, b, 'kafka', 0.5, evidence, {'topics': [topic], 'direction': 'unknown'})


def grpc(g, records):
    defs, servers = {}, {}
    for r in records:
        for proto in r['facts'].get('protos') or []:
            for s in proto['services']:
                defs.setdefault(s['name'], set()).add(r['id'])
        for s in r['facts'].get('grpc_servers') or []:
            servers.setdefault(s['service'], set()).add(r['id'])
    for r in records:
        rid = r['id']
        seen = set()
        for c in r['facts'].get('grpc_clients') or []:
            svc = c['service']
            if svc in seen or (svc not in defs and svc not in servers):
                continue
            seen.add(svc)
            evidence = [ev(rid, c['path'], c['line'], key=f'{svc} client')]
            cands, conf = servers.get(svc, set()) - {rid}, 0.8
            if not cands:
                cands, conf = defs.get(svc, set()) - {rid}, 0.6
            if not cands:
                if rid not in servers.get(svc, set()) and rid not in defs.get(svc, set()):
                    g.miss(rid, 'grpc', svc, 'no server or proto repo', evidence)
                continue
            target = g.choose(cands)
            if target:
                g.add(rid, target, 'grpc', conf, evidence, {'services': [svc]})
            else:
                g.miss(rid, 'grpc', svc, 'ambiguous', evidence, cands)


def scan_root_keys(records):
    """'host/group' prefixes of the scanned roots, from url_key minus the path below the root."""
    roots = set()
    for r in records:
        key, rel = r.get('url_key'), r.get('group_path', '').lower()
        if key and rel and key.endswith('/' + rel):
            roots.add(key[:-len(rel) - 1])
    return roots


def miss_reason(key, roots, match):
    if match:
        return 'ambiguous'
    if roots and not any(key == r or key.startswith(r + '/') for r in roots):
        return 'outside scanned roots'
    return 'no matching repo'


def ci_and_deploy(g, records, url_index):
    hosts = {k.split('/')[0] for k in url_index}
    roots = scan_root_keys(records)
    for r in records:
        f, rid = r['facts'], r['id']
        host = (r.get('url_key') or r['git'].get('remote_key') or '/').split('/')[0]
        ci = f.get('gitlab_ci') or {}
        for inc in ci.get('includes') or []:
            if not inc.get('project'):
                continue
            key = f'{host}/{inc["project"].strip("/").lower()}'
            evidence = [ev(rid, ci['path'], inc.get('line'), key=f'include:project {inc["project"]}')]
            match = url_index.get(key, set()) - {rid}
            target = g.choose(match) if match else None
            if target:
                g.add(rid, target, 'ci', 0.95, evidence, {'files': [inc.get('file')] if inc.get('file') else []})
            else:
                g.miss(rid, 'ci', inc['project'], miss_reason(key, roots, match), evidence, match)
        for app in f.get('argocd') or []:
            for u in app['repo_urls']:
                key = remote_key(u['url'])
                evidence = [ev(rid, app['path'], u['line'], key='repoURL')]
                match = url_index.get(key, set()) - {rid} if key else set()
                target = g.choose(match) if match else None
                if target:
                    g.add(rid, target, 'deploy', 0.9, evidence, {'repo_urls': [u['url']]})
                elif key and key.split('/')[0] in hosts:
                    g.miss(rid, 'deploy', u['url'], miss_reason(key, roots, match), evidence, match)
                else:
                    g.stats['external_urls'] += 1
