# Memory Hub MCP — Requirements and Acceptance

## Goals and Constraints
- Air-gapped deployment (no external internet dependency at runtime).
- SQLite-first persistence model.
- Shared memory across projects plus project-scoped memory.
- `org/*` write access only for `product-owner` and `team-lead`.
- Default TTL: 30 days.
- Sensitive/secrets write blocking.
- Full audit and provenance trail.
- Compatibility surface for Claude, Codex, OpenCode, Gemini, Cursor, Antigravity.
- Makefile-first execution for format, lint, test, and CI checks.

## Scope
Implement a production-ready MCP memory service contract with:
- Unified memory tools (`memory_write`, `memory_read`, `memory_search`, `memory_link`, `memory_audit`, `memory_revalidate`).
- Policy enforcement for ACL, TTL, provenance, and DLP.
- Repeatable verification pipeline with unit + e2e + blackbox checks and coverage gate.

## Non-goals
- External hosted vector databases in v1.
- Internet-dependent enrichment flows in v1.
- Client-specific semantic divergence (adapters are transport/profile wrappers only).

## Acceptance Criteria
1. Required tools are implemented with stable request/response contracts.
2. SQLite schema includes memory, links, audit events, namespaces, roles, and policies.
3. ACL enforcement blocks unauthorized writes to `org/*`.
4. TTL defaults to 30 days and expired records transition to `stale`.
5. Writes without `source_ref` are rejected.
6. Sensitive payloads are blocked and audited as `blocked_sensitive`.
7. `make ci` fails when any of fmt/lint/unit/e2e/blackbox/coverage fails.
8. Coverage gate fails if aggregate coverage is below 80%.


## Usage
- Detailed user guide: `docs/memory-hub-mcp/usage.md`.
