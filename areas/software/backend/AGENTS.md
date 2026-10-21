# Backend

Server-side services: APIs, domain logic, data access, async processing.

## Backend constraints

- Every endpoint has an authorization check, input validation, and a structured error response.
- A schema change ships with a migration file. Never rely on ORM auto-sync in production.
- A new module has structured logs and a latency metric.

## Rules (read on demand)

| Rule | Read when you change |
|:---|:---|
| `architecture.md` | module boundaries, layers, or dependencies |
| `data_access.md` | queries, ORM models, or transactions |
| `security.md` | authentication, authorization, input handling, or secrets |
| `testing.md` | test strategy or test infrastructure |

## Workflows

`/develop-feature`, `/develop-epic`, `/create-endpoint`, `/add-migration`, `/refactor-module`, `/debug-issue`,
`/test-feature`.
