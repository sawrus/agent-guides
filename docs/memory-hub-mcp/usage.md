# Memory Hub MCP — User Guide with Live Examples

This guide explains how to use the implemented Memory Hub MCP locally in air-gapped mode with practical Python examples.

## 1) Quick start

```bash
python3 - <<'PY'
from memory_hub_mcp import MemoryHub

hub = MemoryHub(db_path='memory_hub.sqlite3', ttl_days=30)
print('ready')
PY
```

## 2) Tool map

Implemented tools:
- `memory_write(namespace, record_type, content, source_ref, actor_role)`
- `memory_read(memory_id, include_stale=False)`
- `memory_search(namespace, query, include_stale=False)`
- `memory_link(from_memory_id, to_memory_id, relation, actor_role)`
- `memory_audit(limit=100)`
- `memory_revalidate(memory_id, actor_role, ttl_days=None)`
- `sweeper_mark_stale()`

## 3) Live workflow example (project memory)

```bash
python3 - <<'PY'
from memory_hub_mcp import MemoryHub

hub = MemoryHub(ttl_days=30)

m1 = hub.memory_write(
    namespace='project/payments',
    record_type='decision',
    content='Use SQLite WAL for local Memory Hub persistence',
    source_ref='ADR-42',
    actor_role='developer',
)
print('write#1', m1)

m2 = hub.memory_write(
    namespace='project/payments',
    record_type='task',
    content='Add blackbox tests for all MCP tools',
    source_ref='JIRA-PAY-991',
    actor_role='developer',
)
print('write#2', m2)

one = hub.memory_read(m1['id'])
print('read', one['id'], one['namespace'], one['status'])

found = hub.memory_search('project/payments', 'SQLite')
print('search_count', len(found))

link = hub.memory_link(m1['id'], m2['id'], 'implements', actor_role='developer')
print('link', link)

audit = hub.memory_audit(limit=5)
print('audit_events', [e['event_type'] for e in audit])
PY
```

## 4) org/* ACL example

`org/*` write is allowed only for `product-owner` and `team-lead`.

```bash
python3 - <<'PY'
from memory_hub_mcp import MemoryHub
from memory_hub_mcp.hub import HubError

hub = MemoryHub()

ok = hub.memory_write('org/standards', 'policy', 'Approved release checklist', 'DOC-1', 'product-owner')
print('org_write_ok', ok['id'])

try:
    hub.memory_write('org/standards', 'policy', 'Try override', 'DOC-2', 'developer')
except HubError as e:
    print('org_write_denied', e.code, e.message)
PY
```

Expected deny code: `ACL_DENY`.

## 5) Provenance required example

`source_ref` is mandatory.

```bash
python3 - <<'PY'
from memory_hub_mcp import MemoryHub
from memory_hub_mcp.hub import HubError

hub = MemoryHub()
try:
    hub.memory_write('project/core', 'note', 'Missing provenance', '', 'developer')
except HubError as e:
    print(e.code)
PY
```

Expected code: `PROVENANCE_REQUIRED`.

## 6) DLP / sensitive blocking example

Sensitive payloads are blocked before persistence and logged in audit as `blocked_sensitive`.

```bash
python3 - <<'PY'
from memory_hub_mcp import MemoryHub
from memory_hub_mcp.hub import HubError

hub = MemoryHub()
try:
    hub.memory_write('project/core', 'secret', 'api_key=ABCDEFGHIJKLMNOP', 'SEC-1', 'developer')
except HubError as e:
    print('blocked', e.code)

events = hub.memory_audit(limit=3)
print('latest_event', events[0]['event_type'])
PY
```

Expected:
- error code `SENSITIVE_BLOCKED`
- latest event `blocked_sensitive`

## 7) TTL and revalidation example

```bash
python3 - <<'PY'
from memory_hub_mcp import MemoryHub

hub = MemoryHub(ttl_days=0)
item = hub.memory_write('project/core', 'note', 'Short-lived memory', 'SRC-77', 'developer')

staled = hub.sweeper_mark_stale()
print('staled_count', staled)

revalidated = hub.memory_revalidate(item['id'], actor_role='team-lead', ttl_days=30)
print('revalidated', revalidated['status'])
PY
```

## 8) Run all checks

```bash
make test-unit
make test-e2e
make test-blackbox
make coverage
make ci
```

## 9) Error codes reference

- `ACL_DENY` — role cannot write in selected namespace.
- `PROVENANCE_REQUIRED` — empty or missing `source_ref`.
- `SENSITIVE_BLOCKED` — DLP rejected write.
- `NOT_FOUND` — memory record does not exist.
- `STALE_EXCLUDED` — stale item requested without `include_stale=True`.

## 10) Integration notes for MCP adapters

The current implementation is adapter-agnostic and exposes a stable tool surface at Python API level.
For Claude/Codex/OpenCode/Gemini/Cursor/Antigravity wrappers, map transport layer requests to the same methods without changing business semantics.
