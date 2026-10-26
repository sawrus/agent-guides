"""Static parsers for manifests, CI, env files and source code. Nothing here runs repository code.

Env and config files keep only key names, line numbers and URL hosts. Values are never stored,
except Kafka topic names under *TOPIC* keys whose names do not look like secrets.
"""
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath
import re
import sys
import tomllib

from .common import SECRET_NAME, line_of, norm_pkg, read_text, sanitize_url, url_host

TEST_PATH = re.compile(r'(^|/)(tests?|testing|spec|__tests__|fixtures?)/|(^|/)test_[^/]*$|_test\.(py|go)$|\.spec\.[jt]s$')
ENDPOINT_KEY = re.compile(r'(^|_)(ENDPOINT|URL|URI|BASE_URL|API_URL)S?$')
TOPIC_KEY = re.compile(r'TOPIC')
TOPIC_KEY_SKIP = re.compile(r'PARTITION|REPLICATION|SUFFIX|PREFIX|AUTO_CREATE|RETENTION|COUNT|SIZE')
TOPIC_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{2,}$')
KAFKA_DEPS = re.compile(r'^(kafka-python|aiokafka|confluent-kafka|faust|faust-streaming|kafkajs|node-rdkafka|'
                        r'github\.com/segmentio/kafka-go|github\.com/(ibm|shopify)/sarama|'
                        r'github\.com/confluentinc/confluent-kafka-go.*)$', re.I)
ENV_FILE_PATTERNS = ('*.env', '.env.*', 'env.*', '*.env.*')
# Same rule as extensions/codex/hooks/gate/gate.py SECRET: .env and .env.<x> except example/sample/template.
LOCAL_SECRET_ENV = re.compile(r'^\.env(\.(?!example$|sample$|template$|dist$)[^/]*)?$')
CI_RESERVED = {'stages', 'variables', 'include', 'default', 'workflow', 'image', 'services', 'before_script',
               'after_script', 'cache', 'spec'}
NAME_VARS = ('APPLICATION', 'APP_NAME', 'SERVICE_NAME', 'PROJECT_NAME', 'SERVICE', 'APP')
STDLIB = set(getattr(sys, 'stdlib_module_names', ())) | {'__future__'}


def role_from(text):
    t = text.lower()
    if re.search(r'input|source|consum|subscrib|(^|_)in(_|$)|listen|read', t):
        return 'consumer'
    if re.search(r'output|dest|target|produc|sink|publish|(^|_)out(_|$)|send|write', t):
        return 'producer'
    return 'unknown'


def is_env_file(rel):
    """Committed env templates (*.env, sample.env, .env.example). Local secret files (.env, .env.local) are skipped."""
    name = PurePosixPath(rel).name
    if LOCAL_SECRET_ENV.search(name):
        return False
    if name.endswith(('.py', '.sh', '.ts', '.js', '.go', '.md', '.yml', '.yaml', '.json', '.toml', '.cfg')):
        return False
    return any(fnmatch(name, p) for p in ENV_FILE_PATTERNS)


def parse_env(rel, text):
    keys = []
    for n, line in enumerate(text.splitlines(), 1):
        m = re.match(r'^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*(.*)$', line)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip().strip('"\'')
        entry = {'key': key, 'line': n}
        if not SECRET_NAME.search(key):
            host = url_host(value)
            if host:
                entry['host'] = host
            if TOPIC_KEY.search(key.upper()) and not TOPIC_KEY_SKIP.search(key.upper()) and value:
                topics = [t.strip() for t in value.split(',') if TOPIC_NAME.match(t.strip())]
                if topics:
                    entry['topics'] = topics
        keys.append(entry)
    return {'path': rel, 'keys': keys}


def parse_yaml_env(rel, text):
    """Endpoint and topic keys inside YAML (docker-compose environment, Helm values, k8s env)."""
    keys = []
    lines = text.splitlines()
    for n, line in enumerate(lines, 1):
        pair = re.match(r'^\s*-\s*name:\s*["\']?([A-Z][A-Z0-9_]{2,})["\']?\s*$', line)
        plain = re.match(r'^\s*-?\s*["\']?([A-Z][A-Z0-9_]{2,})["\']?\s*[:=]\s*(.*)$', line)
        if pair:  # k8s style: - name: KEY / value: v
            nxt = re.match(r'^\s*value:\s*(.*)$', lines[n]) if n < len(lines) else None
            key, value = pair.group(1), nxt.group(1) if nxt else ''
        elif plain:
            key, value = plain.group(1), plain.group(2)
        else:
            continue
        upper = key.upper()
        if not (ENDPOINT_KEY.search(upper) or (TOPIC_KEY.search(upper) and not TOPIC_KEY_SKIP.search(upper))):
            continue
        value = value.strip().strip('"\'')
        entry = {'key': key, 'line': n}
        if not SECRET_NAME.search(key):
            host = url_host(value)
            if host:
                entry['host'] = host
            if TOPIC_KEY.search(upper) and value:
                topics = [t.strip() for t in value.split(',') if TOPIC_NAME.match(t.strip())]
                if topics:
                    entry['topics'] = topics
        keys.append(entry)
    return {'path': rel, 'keys': keys} if keys else None


def pep508_name(spec):
    m = re.match(r'^\s*([A-Za-z0-9][A-Za-z0-9._-]*)', spec)
    return m.group(1) if m else None


def parse_pyproject(rel, text):
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        return {'path': rel, 'error': f'toml: {exc}'}
    tool = data.get('tool', {}) if isinstance(data.get('tool'), dict) else {}
    poetry = tool.get('poetry', {}) if isinstance(tool.get('poetry'), dict) else {}
    project = data.get('project', {}) if isinstance(data.get('project'), dict) else {}
    name = poetry.get('name') or project.get('name')
    out = {'path': rel, 'name': name, 'name_line': line_of(text, r'^\s*name\s*=') if name else None,
           'deps': [], 'sources': [], 'packages': []}

    def add(dep, group, value=None):
        if not isinstance(dep, str) or dep.lower() == 'python':
            return
        entry = {'name': dep, 'group': group,
                 'line': line_of(text, rf'^\s*["\']?{re.escape(dep)}["\']?\s*=') or line_of(text, rf'["\']{re.escape(dep)}\b')}
        if isinstance(value, dict):
            if value.get('source'):
                entry['source'] = value['source']
            if value.get('git'):
                entry['git'] = sanitize_url(value['git'])
            if value.get('path'):
                entry['path'] = value['path']
        out['deps'].append(entry)

    for dep, value in (poetry.get('dependencies') or {}).items():
        add(dep, 'main', value)
    for dep, value in (poetry.get('dev-dependencies') or {}).items():
        add(dep, 'dev', value)
    for gname, group in (poetry.get('group') or {}).items():
        if isinstance(group, dict):
            for dep, value in (group.get('dependencies') or {}).items():
                add(dep, gname, value)
    for spec in project.get('dependencies') or []:
        add(pep508_name(spec), 'main')
    for gname, specs in (project.get('optional-dependencies') or {}).items():
        for spec in specs or []:
            add(pep508_name(spec), gname)
    for src in poetry.get('source') or []:
        if isinstance(src, dict):
            out['sources'].append({'name': src.get('name'), 'host': url_host(src.get('url', '')),
                                   'line': line_of(text, rf'^\s*name\s*=\s*["\']{re.escape(str(src.get("name")))}["\']')})
    for pkg in poetry.get('packages') or []:
        if isinstance(pkg, dict) and pkg.get('include'):
            out['packages'].append(pkg['include'].split('/')[0])
    return out


def parse_requirements(rel, text):
    deps, hosts = [], []
    for n, line in enumerate(text.splitlines(), 1):
        line = line.split('#', 1)[0].strip()
        m = re.match(r'^--(?:extra-)?index-url[ =](\S+)', line)
        if m:
            host = url_host(m.group(1))
            if host:
                hosts.append({'host': host, 'line': n})
            continue
        if not line or line.startswith('-'):
            continue
        name = pep508_name(line) if not re.match(r'^(git\+|https?:)', line) else None
        if name:
            deps.append({'name': name, 'line': n})
    return {'path': rel, 'deps': deps, 'index_hosts': hosts}


def parse_package_json(rel, text):
    import json
    try:
        data = json.loads(text)
    except ValueError as exc:
        return {'path': rel, 'error': f'json: {exc}'}
    if not isinstance(data, dict):
        return {'path': rel, 'error': 'not an object'}
    deps = []
    for kind in ('dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies'):
        for dep in (data.get(kind) or {}):
            deps.append({'name': dep, 'group': kind, 'line': line_of(text, rf'"{re.escape(dep)}"\s*:')})
    publish = data.get('publishConfig') or {}
    return {'path': rel, 'name': data.get('name'), 'name_line': line_of(text, r'"name"\s*:'),
            'private': bool(data.get('private')), 'deps': deps,
            'registry_host': url_host(publish.get('registry', '')) if isinstance(publish, dict) else None,
            'scripts': sorted((data.get('scripts') or {}).keys()) if isinstance(data.get('scripts'), dict) else []}


def parse_go_mod(rel, text):
    module = re.search(r'^module\s+(\S+)', text, re.M)
    requires = []
    for n, line in enumerate(text.splitlines(), 1):
        m = re.match(r'^\s*(?:require\s+)?([a-z0-9.-]+\.[a-z]{2,}/\S+)\s+v\S+', line)
        if m and not line.strip().startswith('module'):
            requires.append({'module': m.group(1), 'line': n})
    return {'path': rel, 'module': module.group(1) if module else None,
            'module_line': line_of(text, r'^module\s'), 'requires': requires}


def parse_dockerfile(rel, text):
    froms, expose = [], []
    for n, line in enumerate(text.splitlines(), 1):
        m = re.match(r'^\s*FROM\s+(?:--\S+\s+)*(\S+)', line, re.I)
        if m:
            froms.append({'image': sanitize_url(m.group(1)), 'line': n})
        m = re.match(r'^\s*EXPOSE\s+(.+)$', line, re.I)
        if m:
            expose.extend(m.group(1).split())
    return {'path': rel, 'from': froms, 'expose': expose}


def parse_compose(rel, text):
    services, in_services = [], False
    for line in text.splitlines():
        if re.match(r'^services:\s*$', line):
            in_services = True
            continue
        if in_services:
            if re.match(r'^\S', line):
                in_services = False
                continue
            m = re.match(r'^ {2}([A-Za-z0-9_.-]+):\s*$', line) or re.match(r'^\t([A-Za-z0-9_.-]+):\s*$', line)
            if m:
                services.append(m.group(1))
    return {'path': rel, 'services': services}


def parse_chart(rel, text):
    name = re.search(r'^name:\s*["\']?([\w.-]+)', text, re.M)
    deps = []
    for m in re.finditer(r'^\s*-\s*name:\s*["\']?([\w.-]+)["\']?\s*$([\s\S]*?)(?=^\s*-\s*name:|\Z)', text, re.M):
        repo = re.search(r'repository:\s*["\']?(\S+?)["\']?\s*$', m.group(2), re.M)
        deps.append({'name': m.group(1), 'repository_host': url_host(repo.group(1)) if repo else None})
    return {'path': rel, 'name': name.group(1) if name else None, 'dependencies': deps}


def parse_argocd(rel, text):
    if not re.search(r'^kind:\s*(Application|ApplicationSet|AppProject)\s*$', text, re.M):
        return None
    urls = []
    for n, line in enumerate(text.splitlines(), 1):
        m = re.match(r'^\s*-?\s*repoURL:\s*["\']?([^"\'\s]+)', line)
        if m:
            urls.append({'url': sanitize_url(m.group(1)), 'line': n})
    kinds = sorted(set(re.findall(r'^kind:\s*(\w+)', text, re.M)))
    return {'path': rel, 'kinds': kinds, 'repo_urls': urls}


def parse_makefile(texts):
    """texts: list of (rel, text). Returns targets with evidence and selected name variables."""
    targets, variables, includes = {}, {}, []
    for rel, text in texts:
        for n, line in enumerate(text.splitlines(), 1):
            m = re.match(r'^([A-Za-z][\w.-]*)\s*:(?!=)', line)
            if m and m.group(1) not in targets and not m.group(1).startswith('.'):
                targets[m.group(1)] = {'path': rel, 'line': n}
            m = re.match(rf'^({"|".join(NAME_VARS)})\s*[:?]?=\s*([A-Za-z0-9._-]+)\s*$', line)
            if m:
                variables.setdefault(m.group(1), {'value': m.group(2), 'path': rel, 'line': n})
            m = re.match(r'^-?include\s+(.+)$', line)
            if m:
                includes.extend(m.group(1).split())
    return {'targets': targets, 'name_vars': variables, 'includes': includes}


def parse_gitlab_ci(rel, text):
    lines = text.splitlines()
    blocks, current = [], None
    for n, line in enumerate(lines, 1):
        m = re.match(r'^([^\s#][^:]*?):\s*(.*)$', line)
        if m and not line.startswith(('-', ' ')):
            current = {'name': m.group(1).strip().strip('"\''), 'line': n, 'inline': m.group(2), 'body': []}
            blocks.append(current)
        elif current is not None:
            current['body'].append((n, line))
    jobs, stages, includes = [], [], []
    for block in blocks:
        name = block['name']
        if name == 'stages':
            stages = [re.sub(r'^\s*-\s*', '', l).strip().strip('"\'') for _, l in block['body'] if l.strip().startswith('-')]
        elif name == 'include':
            includes.extend(parse_ci_include(block))
        elif name not in CI_RESERVED and not name.startswith('.'):
            jobs.append(ci_job(block))
    return {'path': rel, 'stages': stages, 'jobs': jobs, 'includes': includes}


def parse_ci_include(block):
    out, cur = [], None
    if block['inline'].strip():
        return [{'local': block['inline'].strip().strip('"\''), 'line': block['line']}]
    for n, line in block['body']:
        m = re.match(r'^\s*(-\s*)?(project|file|ref|local|template|remote|component):\s*["\']?([^"\'#]*?)["\']?\s*$', line)
        if m:
            if m.group(1) or cur is None or m.group(2) in cur:
                cur = {'line': n}
                out.append(cur)
            value = m.group(3)
            cur[m.group(2)] = sanitize_url(value) if m.group(2) == 'remote' else value
        elif re.match(r'^\s*-\s*["\']?[^:]+["\']?\s*$', line):
            out.append({'local': line.strip().lstrip('-').strip().strip('"\''), 'line': n})
            cur = None
    return out


def ci_job(block):
    job = {'name': block['name'], 'line': block['line'], 'stage': None, 'script': []}
    in_script, indent = False, None
    for n, line in block['body']:
        m = re.match(r'^(\s+)stage:\s*["\']?([\w.-]+)', line)
        if m:
            job['stage'] = m.group(2)
        m = re.match(r'^(\s+)script:\s*(.*)$', line)
        if m:
            in_script, indent = True, len(m.group(1))
            if m.group(2).strip() and not m.group(2).strip().startswith('|'):
                job['script'].append({'cmd': m.group(2).strip().strip('[]"\''), 'line': n})
            continue
        if in_script:
            stripped = line.strip()
            cur_indent = len(line) - len(line.lstrip())
            if stripped and cur_indent <= indent and not stripped.startswith('-'):
                in_script = False
            elif stripped.startswith('- '):
                job['script'].append({'cmd': stripped[2:].strip().strip('"\''), 'line': n})
    return job


def parse_github_workflow(rel, text):
    jobs = re.findall(r'^  ([A-Za-z0-9_-]+):\s*$', text, re.M)
    runs = []
    for n, line in enumerate(text.splitlines(), 1):
        m = re.match(r'^\s*(?:-\s*)?run:\s*(.+)$', line)
        if m and m.group(1).strip() not in ('|', '>'):
            runs.append({'cmd': m.group(1).strip(), 'line': n})
    return {'path': rel, 'jobs': jobs, 'runs': runs}


def parse_proto(rel, text):
    package = re.search(r'^\s*package\s+([\w.]+)\s*;', text, re.M)
    services = [{'name': m.group(1), 'line': text.count('\n', 0, m.start()) + 1}
                for m in re.finditer(r'^\s*service\s+(\w+)\s*\{', text, re.M)]
    return {'path': rel, 'package': package.group(1) if package else None, 'services': services}


KAFKA_CODE = [
    (re.compile(r'KafkaConsumer\(\s*["\']([^"\']+)'), 'consumer'),
    (re.compile(r'\.subscribe\(\s*\[?\s*["\']([^"\']+)'), 'consumer'),
    (re.compile(r'\.(?:send|send_and_wait|produce)\(\s*["\']([^"\']+)'), 'producer'),
    (re.compile(r'(?:getenv|environ\.get)\(\s*["\'](\w*TOPIC\w*)["\']\s*,\s*["\']([^"\'{}$%]+)["\']'), None),
    (re.compile(r'\b(\w*topic\w*)\s*[:=]\s*["\']([^"\'{}$%]+)["\']', re.I), None),
]
GRPC_CLIENT = [re.compile(r'\b(\w+)Stub\('), re.compile(r'\bNew(\w+)Client\(')]
GRPC_SERVER = [re.compile(r'add_(\w+)Servicer_to_server'), re.compile(r'\bRegister(\w+)Server\(')]
PY_IMPORT = re.compile(r'^[ \t]*(?:from\s+([A-Za-z_]\w*)[\w.]*\s+import\b|import\s+([A-Za-z_][\w.]*(?:\s*,\s*[A-Za-z_][\w.]*)*))', re.M)
GETENV = re.compile(r'(?:getenv|environ\.get|environ\[|env\()\s*\(?\s*["\']([A-Z][A-Z0-9_]{2,})["\']')
SETTINGS_FIELD = re.compile(r'^\s+([a-z][a-z0-9_]*_(?:endpoint|url|uri))\s*:\s*', re.M)


def scan_code(rel, text, out):
    is_test = bool(TEST_PATH.search(rel))
    ext = PurePosixPath(rel).suffix
    if ext == '.py' and not is_test:
        for m in PY_IMPORT.finditer(text):
            names = [m.group(1)] if m.group(1) else [x.strip().split('.')[0] for x in m.group(2).split(',')]
            for name in names:
                if name in STDLIB:
                    continue
                entry = out['imports'].setdefault(name, {'path': rel, 'line': text.count('\n', 0, m.start()) + 1,
                                                         'count': 0})
                entry['count'] += 1
        if 'BaseSettings' in text:
            for m in SETTINGS_FIELD.finditer(text):
                out['code_keys'].append({'key': m.group(1).upper(), 'path': rel,
                                         'line': text.count('\n', 0, m.start()) + 1})
    if ext in ('.py', '.go', '.js', '.ts') and not is_test:
        for m in GETENV.finditer(text):
            key = m.group(1)
            if ENDPOINT_KEY.search(key) or (TOPIC_KEY.search(key) and not TOPIC_KEY_SKIP.search(key)):
                out['code_keys'].append({'key': key, 'path': rel, 'line': text.count('\n', 0, m.start()) + 1})
        if 'kafka' in text.lower():
            out['kafka_hint'] = True
        for pattern, role in KAFKA_CODE:
            for m in pattern.finditer(text):
                topic = m.group(m.lastindex)
                if not TOPIC_NAME.match(topic) or topic.replace('.', '').isdigit():
                    continue
                if role is None and (not TOPIC_KEY.search(m.group(1).upper()) or TOPIC_KEY_SKIP.search(m.group(1).upper())):
                    continue
                line = text.count('\n', 0, m.start()) + 1
                found = role
                if found is None:
                    found = role_from(m.group(1))
                    if found == 'unknown':  # look at the call around the literal
                        window = '\n'.join(text.splitlines()[max(0, line - 4):line + 1])
                        found = role_from(' '.join(re.findall(r'send|produce|publish|subscribe|consume|poll', window)))
                out['kafka_code'].append({'topic': topic, 'role': found, 'path': rel, 'line': line})
        for pattern in GRPC_CLIENT:
            for m in pattern.finditer(text):
                if 'grpc' in text.lower():
                    out['grpc_clients'].append({'service': m.group(1), 'path': rel,
                                                'line': text.count('\n', 0, m.start()) + 1})
        for pattern in GRPC_SERVER:
            for m in pattern.finditer(text):
                out['grpc_servers'].append({'service': m.group(1), 'path': rel,
                                            'line': text.count('\n', 0, m.start()) + 1})


def python_modules(files, pyproject):
    mods = set()
    for rel in files:
        parts = PurePosixPath(rel).parts
        if len(parts) == 2 and parts[1] == '__init__.py':
            mods.add(parts[0])
        elif len(parts) == 3 and parts[0] == 'src' and parts[2] == '__init__.py':
            mods.add(parts[1])
    for p in (pyproject or {}).get('packages') or []:
        mods.add(p)
    return sorted(m for m in mods if m.isidentifier())


def parse_repo(repo, files):
    """All static facts of one repository."""
    repo = Path(repo)
    out = {'pyproject': None, 'requirements': [], 'setup_name': None, 'package_json': [], 'go_mod': [],
           'dockerfiles': [], 'compose': [], 'helm': [], 'argocd': [], 'env': [], 'code_keys': [],
           'imports': {}, 'kafka_code': [], 'kafka_hint': False, 'protos': [], 'grpc_clients': [],
           'grpc_servers': [], 'gitlab_ci': None, 'github': [], 'make_texts': []}
    file_set = set(files)
    for rel in files:
        path = PurePosixPath(rel)
        name, depth = path.name, len(path.parts)
        ext = path.suffix.lower()
        wanted = (
            name in ('pyproject.toml', 'setup.py', 'setup.cfg', 'package.json', 'go.mod', 'Chart.yaml', '.gitlab-ci.yml')
            or name.startswith('Dockerfile') or name.startswith(('requirements', 'docker-compose', 'compose.'))
            or is_env_file(rel) or ext in ('.py', '.go', '.js', '.ts', '.proto')
            or (ext in ('.yml', '.yaml') and ('values' in name or 'argocd' in rel.lower() or 'deploy' in rel.lower()
                                              or 'helm' in rel.lower() or 'k8s' in rel.lower() or 'apps' in rel.lower()))
            or (depth == 1 and (name in ('Makefile', 'makefile', 'GNUmakefile') or ext == '.mk'))
            or (rel.startswith('.github/workflows/') and ext in ('.yml', '.yaml'))
        )
        if not wanted or 'node_modules/' in rel:
            continue
        text = read_text(repo / rel)
        if text is None:
            continue
        if name == 'pyproject.toml' and depth == 1:
            out['pyproject'] = parse_pyproject(rel, text)
        elif name in ('setup.py', 'setup.cfg') and depth == 1:
            m = re.search(r'\bname\s*[=:]\s*["\']?([A-Za-z0-9._-]+)', text)
            if m:
                out['setup_name'] = {'name': m.group(1), 'path': rel, 'line': line_of(text, r'\bname\s*[=:]')}
        elif name.startswith('requirements') and ext in ('.txt', '.in'):
            out['requirements'].append(parse_requirements(rel, text))
        elif name == 'package.json':
            out['package_json'].append(parse_package_json(rel, text))
        elif name == 'go.mod':
            out['go_mod'].append(parse_go_mod(rel, text))
        elif name.startswith('Dockerfile'):
            out['dockerfiles'].append(parse_dockerfile(rel, text))
        elif name == 'Chart.yaml':
            if not ('/charts/' in rel and f'{rel.split("/charts/")[0]}/Chart.yaml' in file_set):
                out['helm'].append(parse_chart(rel, text))
        elif name == '.gitlab-ci.yml' and depth == 1:
            out['gitlab_ci'] = parse_gitlab_ci(rel, text)
        elif rel.startswith('.github/workflows/'):
            out['github'].append(parse_github_workflow(rel, text))
        elif depth == 1 and (name in ('Makefile', 'makefile', 'GNUmakefile') or ext == '.mk'):
            out['make_texts'].append((rel, text))
        elif ext == '.proto':
            out['protos'].append(parse_proto(rel, text))
        elif is_env_file(rel):
            out['env'].append(parse_env(rel, text))
        elif ext in ('.py', '.go', '.js', '.ts'):
            scan_code(rel, text, out)
        if ext in ('.yml', '.yaml'):
            if name.startswith(('docker-compose', 'compose.')):
                out['compose'].append(parse_compose(rel, text))
            argo = parse_argocd(rel, text)
            if argo:
                out['argocd'].append(argo)
            # Vendored subcharts and Go templates describe third-party software, not this repository.
            vendored = '/charts/' in rel and f'{rel.split("/charts/")[0]}/Chart.yaml' in file_set
            if not TEST_PATH.search(rel) and not vendored and '/templates/' not in f'/{rel}':
                env = parse_yaml_env(rel, text)
                if env:
                    out['env'].append(env)
    out['makefile'] = parse_makefile(sorted(out.pop('make_texts'), key=lambda t: t[0] != 'Makefile'))
    out['python_modules'] = python_modules(files, out['pyproject'])
    deps = all_deps(out)
    if any(KAFKA_DEPS.match(d['name']) for d in deps) or any('KAFKA' in k['key'].upper() for e in out['env'] for k in e['keys']):
        out['kafka_hint'] = True
    return out


def all_deps(facts):
    """Flat list of declared dependencies across ecosystems with evidence."""
    deps = []
    py = facts.get('pyproject') or {}
    for d in py.get('deps') or []:
        deps.append({'eco': 'python', 'name': d['name'], 'path': py['path'], 'line': d.get('line'),
                     'source': d.get('source'), 'group': d.get('group')})
    for req in facts.get('requirements') or []:
        for d in req['deps']:
            deps.append({'eco': 'python', 'name': d['name'], 'path': req['path'], 'line': d['line']})
    for pj in facts.get('package_json') or []:
        for d in pj.get('deps') or []:
            deps.append({'eco': 'npm', 'name': d['name'], 'path': pj['path'], 'line': d.get('line'), 'group': d['group']})
    for gm in facts.get('go_mod') or []:
        for d in gm['requires']:
            deps.append({'eco': 'go', 'name': d['module'], 'path': gm['path'], 'line': d['line']})
    return deps


def dep_names(facts):
    return {norm_pkg(d['name']) for d in all_deps(facts)}
