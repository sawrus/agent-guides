---
name: add-migration
type: workflow
trigger: /add-migration
description: Add a backward-compatible database schema migration with rollback and tests.
inputs:
  - schema_change
outputs:
  - migration_file
  - tests
  - docs_page
selection:
  general: false
  use-when: "The request asks to add, rename, drop or change a table, column, index or constraint in a service database through a migration."
  avoid-when: "Analytics warehouse models or dbt changes, or a request that only changes queries."
uses-skills: []
related-rules:
  - data_access.md
  - testing.md
checks:
  - make lint
  - make test
artifacts:
  - docs/<service>.md
---

# Add a migration

Example request: `/add-migration "Rename users.full_name to users.display_name"`

## Steps

### 1. Read the current schema

- **Do:** find the migration tool and its head revision (`alembic heads`, `flyway info`, `goose status`). Read
  the current table definition and every query that reads or writes the affected columns (`grep -rn`).
  Estimate the table size from the docs page or ask the user.
- **Done when:** you can list the affected tables, columns, indexes, and code paths.

### 2. Plan expand and contract

- **Do:** split a breaking change into releases: expand (add nullable column, new table, or index), switch code
  to dual write and read, backfill, then contract (drop) in a later change. Mark locking operations on large
  tables and plan `CONCURRENTLY` or `NOT VALID` variants.
- **Done when:** the plan says which release runs each migration and the running code works after every step.

### 3. Write the migration and code

- **Do:** generate the file with the project tool (`alembic revision -m "<msg>"`, a new `V<n>__<msg>.sql`),
  write `upgrade` and `downgrade`, and change the code for this release only. Put a backfill in a separate,
  batched, resumable step.
- **Done when:** the migration has a downgrade or a comment that says why rollback is impossible.

### 4. Test up and down

- **Do:** run upgrade, downgrade, and upgrade again on a clean database (Testcontainers or `docker compose`).
  Run the repository tests against the migrated schema.
- **Done when:** all three runs succeed and the tests pass.

### 5. Document and hand over

- **Do:** update the service docs page (schema, rollout order, rollback). Run every command in `checks`.
  Ask the user first before you run the migration or the backfill against a shared or production database.
- **Done when:** all `checks` commands exit 0 and the docs page lists the rollout and rollback steps.
