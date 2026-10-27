"""T11 grader: the orders-api Deployment ships 1.4.2 and meets the Kubernetes rules that exist in every rule version.

Usage: check_t11.py <project>. Exit 0 when every item holds; otherwise print the failed items and exit 1.
Stdlib only: a small YAML subset parser (block maps and sequences, flow [..] and {..}, quoted scalars,
comments, `---` documents, `|`/`>` block scalars). A manifest outside that subset fails the check.

Rule items (present both before and after the content cleanup, `areas/devops/kubernetes/rules/`):
- resource-governance: requests.cpu, requests.memory, and limits.memory on every container;
- workload-security: runAsNonRoot true, non-zero runAsUser, allowPrivilegeEscalation false,
  readOnlyRootFilesystem true, capabilities.drop ALL, seccompProfile RuntimeDefault on every container
  (pod-level values count for the fields Kubernetes inherits); a dedicated ServiceAccount (not `default`)
  defined in k8s/, with automountServiceAccountToken false on the pod or the ServiceAccount.
Task items: image tag 1.4.2, env FEATURE_RETURNS=enabled, and the existing port, probes, and DATABASE_URL kept.
"""
import re
import sys
from pathlib import Path

IMAGE = 'registry.example.com/shop/orders-api:1.4.2'
KEY = re.compile(r'''^("[^"]*"|'[^']*'|[^\s'"\[\]{}#,-][^:#]*?|-[^\s:][^:#]*?)\s*:(?:\s+(.*))?$''')


def strip_comment(line):
    quote = None
    for i, ch in enumerate(line):
        if quote:
            quote = None if ch == quote else quote
        elif ch in '"\'':
            quote = ch
        elif ch == '#' and (i == 0 or line[i - 1] in ' \t'):
            return line[:i].rstrip()
    return line.rstrip()


def scalar(text):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in '"\'':
        return text[1:-1]
    low = text.lower()
    if low in ('true', 'false'):
        return low == 'true'
    if low in ('null', '~', ''):
        return None
    if re.fullmatch(r'[-+]?\d+', text):
        return int(text)
    return text


def flow(text):
    """Parse a flow value: [a, b], {k: v}, nested, or a plain scalar."""
    value, rest = _flow(text.strip())
    if rest.strip():
        raise ValueError(f'unexpected text after flow value: {rest!r}')
    return value


def _flow(s):
    s = s.lstrip()
    if s[:1] in '[{':
        closing, out, s = (']', [], s[1:]) if s[0] == '[' else ('}', {}, s[1:])
        while True:
            s = s.lstrip()
            if s[:1] == closing:
                return out, s[1:]
            if closing == '}':
                match = re.match(r'''("[^"]*"|'[^']*'|[^:,}]+?)\s*:\s*''', s)
                if not match:
                    raise ValueError(f'bad flow mapping: {s!r}')
                value, s = _flow(s[match.end():])
                out[scalar(match.group(1))] = value
            else:
                value, s = _flow(s)
                out.append(value)
            s = s.lstrip()
            if s[:1] == ',':
                s = s[1:]
            elif s[:1] != closing:
                raise ValueError(f'bad flow collection: {s!r}')
    match = re.match(r'''"[^"]*"|'[^']*'|[^,\]}]*''', s)
    return scalar(match.group(0)), s[match.end():]


class Parser:
    def __init__(self, lines):
        self.lines = [(len(raw) - len(raw.lstrip(' ')), text.strip()) for raw in lines
                      if (text := strip_comment(raw)).strip()]

    def parse(self):
        if not self.lines:
            return None
        value, i = self.node(0, self.lines[0][0])
        if i != len(self.lines):
            raise ValueError(f'unparsed line: {self.lines[i][1]!r}')
        return value

    def node(self, i, indent):
        text = self.lines[i][1]
        if text == '-' or text.startswith('- '):
            return self.sequence(i, indent)
        if KEY.match(text):
            return self.mapping(i, indent)
        return flow(text), i + 1

    def sequence(self, i, indent):
        items = []
        while i < len(self.lines) and self.lines[i][0] == indent and (self.lines[i][1] == '-' or self.lines[i][1].startswith('- ')):
            text = self.lines[i][1]
            rest = text[1:].lstrip()
            if not rest:
                if i + 1 < len(self.lines) and self.lines[i + 1][0] > indent:
                    value, i = self.node(i + 1, self.lines[i + 1][0])
                else:
                    value, i = None, i + 1
            else:
                child = indent + len(text) - len(rest)
                self.lines[i] = (child, rest)
                value, i = self.node(i, child)
            items.append(value)
        return items, i

    def mapping(self, i, indent):
        out = {}
        while i < len(self.lines) and self.lines[i][0] == indent:
            match = KEY.match(self.lines[i][1])
            if not match or self.lines[i][1].startswith('- '):
                break
            key, rest = scalar(match.group(1)), (match.group(2) or '').strip()
            i += 1
            if not rest:
                if i < len(self.lines) and (self.lines[i][0] > indent or
                                            (self.lines[i][0] == indent and self.lines[i][1].startswith('-'))):
                    value, i = self.node(i, self.lines[i][0])
                else:
                    value = None
            elif rest[0] in '|>':
                block = []
                while i < len(self.lines) and self.lines[i][0] > indent:
                    block.append(self.lines[i][1])
                    i += 1
                value = ('\n' if rest[0] == '|' else ' ').join(block)
            else:
                value = flow(rest)
            out[key] = value
        if i < len(self.lines) and self.lines[i][0] > indent:
            raise ValueError(f'bad indentation: {self.lines[i][1]!r}')
        return out, i


def documents(text):
    doc = []
    for raw in text.splitlines():
        if raw.rstrip() == '---' or raw.startswith('--- '):
            yield Parser(doc).parse()
            doc = []
        else:
            doc.append(raw.replace('\t', '    '))
    yield Parser(doc).parse()


def get(data, *path):
    for key in path:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def check(project):
    failures = []
    docs = []
    for path in sorted((Path(project) / 'k8s').rglob('*.y*ml')):
        try:
            docs += [d for d in documents(path.read_text()) if isinstance(d, dict)]
        except (ValueError, IndexError) as error:
            return [f'{path.name}: cannot parse ({error})']
    deployments = [d for d in docs if d.get('kind') == 'Deployment' and get(d, 'metadata', 'name') == 'orders-api']
    if len(deployments) != 1:
        return [f'expected one orders-api Deployment, found {len(deployments)}']
    pod = get(deployments[0], 'spec', 'template', 'spec') or {}
    containers = [c for c in (pod.get('containers') or []) + (pod.get('initContainers') or []) if isinstance(c, dict)]
    main = [c for c in containers if c.get('name') == 'orders-api']
    if len(main) != 1:
        return ['container orders-api is missing']
    main = main[0]
    if main.get('image') not in (IMAGE,) and not str(main.get('image', '')).startswith(IMAGE + '@sha256:'):
        failures.append(f'image is {main.get("image")!r}, expected {IMAGE}')
    env = {e.get('name'): e for e in main.get('env') or [] if isinstance(e, dict)}
    if str(get(env, 'FEATURE_RETURNS', 'value')) != 'enabled':
        failures.append('env FEATURE_RETURNS=enabled is missing')
    if get(env, 'DATABASE_URL', 'valueFrom', 'secretKeyRef', 'name') != 'orders-db':
        failures.append('env DATABASE_URL from secret orders-db was changed')
    if 8080 not in [p.get('containerPort') for p in main.get('ports') or [] if isinstance(p, dict)]:
        failures.append('containerPort 8080 was removed')
    for probe in ('readinessProbe', 'livenessProbe'):
        if not main.get(probe):
            failures.append(f'{probe} was removed')
    pod_security = pod.get('securityContext') or {}
    for c in containers:
        name, security = c.get('name'), c.get('securityContext') or {}
        for path in (('requests', 'cpu'), ('requests', 'memory'), ('limits', 'memory')):
            if get(c, 'resources', *path) in (None, ''):
                failures.append(f'{name}: resources.{".".join(path)} is missing')

        def field(*path, inherited=False):
            value = get(security, *path)
            return get(pod_security, *path) if value is None and inherited else value
        if field('runAsNonRoot', inherited=True) is not True:
            failures.append(f'{name}: runAsNonRoot is not true')
        user = field('runAsUser', inherited=True)
        if not isinstance(user, int) or user <= 0:
            failures.append(f'{name}: runAsUser is not a non-zero UID')
        if field('allowPrivilegeEscalation') is not False:
            failures.append(f'{name}: allowPrivilegeEscalation is not false')
        if field('readOnlyRootFilesystem') is not True:
            failures.append(f'{name}: readOnlyRootFilesystem is not true')
        if [str(x).upper() for x in field('capabilities', 'drop') or []] != ['ALL']:
            failures.append(f'{name}: capabilities.drop is not ["ALL"]')
        if field('seccompProfile', 'type', inherited=True) != 'RuntimeDefault':
            failures.append(f'{name}: seccompProfile.type is not RuntimeDefault')
        if security.get('privileged') is True:
            failures.append(f'{name}: privileged is true')
    account = pod.get('serviceAccountName') or pod.get('serviceAccount')
    if not account or account == 'default':
        failures.append('no dedicated serviceAccountName')
    else:
        accounts = [d for d in docs if d.get('kind') == 'ServiceAccount' and get(d, 'metadata', 'name') == account]
        if not accounts:
            failures.append(f'ServiceAccount {account} is not defined in k8s/')
        automount = pod.get('automountServiceAccountToken')
        if automount is None and accounts:
            automount = accounts[0].get('automountServiceAccountToken')
        if automount is not False:
            failures.append('automountServiceAccountToken is not false')
    return failures


if __name__ == '__main__':
    problems = check(sys.argv[1])
    print('\n'.join(problems) or 'T11 manifest: ok')
    raise SystemExit(1 if problems else 0)
