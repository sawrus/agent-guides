# Memory Hub MCP — Architecture and Policy Model

## Logical Architecture
1. **MCP API Layer**
   - Exposes unified tools used by all clients.
2. **Policy Engine**
   - ACL checks, provenance validation, TTL rules, conflict-priority resolver.
3. **DLP/Security Guard**
   - Secret and sensitive content detection before persistence.
4. **Persistence Layer (SQLite-first)**
   - Canonical storage and indexes (B-tree + FTS).
5. **Audit/Provenance Layer**
   - Append-only event stream for all write/read-sensitive actions.

## Data Model (v1)
Core tables:
- `memories`
- `memory_links`
- `memory_events` (append-only)
- `namespaces`
- `roles`
- `access_policies`

Key fields:
- `namespace`, `record_type`, `content`, `source_ref`, `created_by_role`
- `created_at`, `expires_at`, `status` (`active|stale|blocked`)
- `sensitivity_flag`, `hash`

Indexes:
- B-tree: `namespace`, `record_type`, `status`, `expires_at`
- FTS over `content`
- Optional semantic index extension (post-v1)

## Policy Contracts
### ACL
- `org/*`: write allowed only for `product-owner`, `team-lead`.
- `project/*`: configurable role matrix.

### TTL
- Default `expires_at = created_at + 30 days`.
- Sweeper transitions expired records to `stale`.
- Search excludes `stale` by default unless explicitly included.

### Conflict Priority
`code > approved_adr > memory`

### Provenance
- Missing `source_ref` on write is a hard reject.

## Threat Model (v1)
Primary risks and mitigations:
- **Secret leakage** → pre-write DLP + block + audit event.
- **Unauthorized org writes** → deterministic ACL checks + deny audit.
- **Stale memory misuse** → default filtering + explicit revalidation flow.
- **SQLite lock contention** → WAL mode + bounded retries + batched writes.
