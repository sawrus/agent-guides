---
trigger: manual
description: ORM usage, query patterns, transactions, and N+1 prevention
---
# Rule: Data Access & State Management

**Priority**: P0 — Data integrity violations are critical.

## Constraints

1. **Polyglot persistence roles**
   - **PostgreSQL**: primary source of truth for OLTP transactions.
   - **Redis**: cache, rate-limiting, distributed locks, and transient Pub/Sub only.
   - **ClickHouse**: analytics/time-series/high-volume OLAP workloads.

2. **Migration protocol**
   - All schema migrations must be versioned.
   - Migrations must remain backward compatible.
   - Breaking changes follow Expand-and-Contract: add new -> dual write/read -> remove old.

3. **Performance and query hygiene**
   - N+1 queries are forbidden; use joins, eager loading, or DataLoader patterns.
   - `SELECT *` is disallowed.
   - Avoid long-running transactions; external I/O must not run inside DB transactions.
