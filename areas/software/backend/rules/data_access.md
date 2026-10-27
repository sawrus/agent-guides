---
description: Queries, transactions, and schema migrations for relational stores used by backend services.
paths:
  - "**/repositories/**"
  - "**/repository/**"
  - "**/migrations/**"
  - "**/alembic/**"
  - "**/db/migration/**"
  - "**/*.sql"
---

# Data access and migrations

- Use parameterized queries or the ORM query builder; never build SQL by string concatenation or f-strings.
- Do not use `SELECT *` in application queries; name the columns.
- Remove N+1 queries: load relations with a join, `selectinload`/`JOIN FETCH`, or one batched query.
- Add an index for every new column used in a `WHERE`, `JOIN`, or `ORDER BY` of a hot query; check with `EXPLAIN`.
- Keep transactions short; set a statement timeout (`statement_timeout`, `QueryTimeout`) for request paths.
- Use PostgreSQL as the source of truth; use Redis only for cache, rate limits, locks, and transient data.
- Change the schema only through a versioned migration file (Alembic, Flyway, Liquibase, goose, golang-migrate).
- Never enable ORM auto-sync (`create_all`, `ddl-auto=update`, `AutoMigrate`) outside tests.
- Write a downgrade for every migration, or state in the migration file why rollback is not possible.
- Keep each migration backward compatible with the running code: expand (add), migrate data, then contract (drop) in a later release.
- Do not rename or drop a column in the same release that stops using it.
- Create indexes on large PostgreSQL tables with `CREATE INDEX CONCURRENTLY` in a migration without a transaction.
- Add `NOT NULL` to an existing column only after a backfill, and add the constraint as `NOT VALID` first.
- Run every migration up and down against a clean database in the test suite.
