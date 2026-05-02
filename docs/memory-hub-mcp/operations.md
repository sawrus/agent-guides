# Memory Hub MCP — Operations Runbook

## Runtime profile
- Air-gapped deployment profile.
- SQLite local persistence with WAL enabled.
- Scheduled sweeper for TTL and stale transitions.

## Operational Commands
- `make fmt`
- `make lint`
- `make test-unit`
- `make test-e2e`
- `make test-blackbox`
- `make coverage`
- `make test`
- `make ci`

## Backup and Restore
1. Stop writes (maintenance mode).
2. Snapshot SQLite DB and corresponding WAL files.
3. Validate snapshot by opening DB and running integrity check.
4. Restore by replacing DB/WAL and replaying startup checks.

## Audit Review
- `memory_events` is append-only and immutable by policy.
- Mandatory event coverage:
  - write accepted
  - write denied (ACL)
  - write blocked (`blocked_sensitive`)
  - revalidation actions
- Investigations should rely on event timestamps, actor role, namespace, reason code, and source reference.

## Incident Handling
- DLP false positive: use allowlist process with explicit rationale; never bypass audit.
- Lock contention spikes: verify WAL mode, retry thresholds, and write batching.
- Client drift: execute blackbox contract suite against each adapter profile.
