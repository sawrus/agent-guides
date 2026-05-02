# Memory Hub MCP — Test Plan

## Pass Criteria
- Unit tests: pass
- E2E tests: pass
- Blackbox tests: pass
- Aggregate coverage: **>= 80%**

## Unit Matrix
Cover:
- ACL decision matrix
- TTL calculations and boundary dates
- DLP detectors (regex + entropy + deny-list)
- Conflict-priority resolver (`code > approved_adr > memory`)
- Provenance/source validation

## E2E Scenarios
1. `product-owner` writes to `org/*` → success.
2. `developer` writes to `org/*` → denied.
3. Missing `source_ref` → denied.
4. Secret-containing payload → denied + `blocked_sensitive` audit event.
5. `project/*` write/read/search/link flow → success.
6. TTL expiration transition to `stale` + `memory_revalidate` recovery.

## Blackbox Scenarios
API-only checks through MCP tools:
- Empty payloads
- Long payloads
- Namespace/role conflicts
- Parallel write attempts
- Contract consistency across all 6 client adapters

## Coverage Strategy
- `make coverage` aggregates all test suites.
- Coverage command fails hard below threshold.
- Coverage report artifact path: `reports/coverage/`.
