---
trigger: glob
paths:
  - "**/migrations/**"
  - "**/alembic/**"
  - "**/*.sql"
  - "**/db/**"
  - "**/scripts/**"
  - "**/.env.example"
description: Safety rules for agents and scripts that connect to a real database (production, replicas, shared stages)
---
# Rule: Database safety

**Priority**: P0. A write or a maintenance command on a shared database can damage data or the service.

## Rules

1. Treat every non-local database as production. Non-local means any host other than `localhost`, `127.*`, `::1`,
   a unix socket, or `sqlite`. A replica is production.
2. Never run write or maintenance SQL on a non-local database: `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `TRUNCATE`,
   `DROP`, `ALTER`, `CREATE INDEX`, `GRANT`, `REVOKE`, `COPY ... FROM`, `VACUUM`, `ANALYZE`, `REINDEX`,
   `CLUSTER`, `REFRESH MATERIALIZED VIEW`, `pg_terminate_backend`. Show the statement to the user and let them run it.
3. Ask the user before a script or command uses credentials from `.env` or the environment (`load_dotenv`,
   `source .env`, `DATABASE_URL`). Say which host it reaches and why.
4. For a read-only investigation on a non-local database, open a read-only session
   (`SET default_transaction_read_only = on`) and set `statement_timeout`. Prefer `EXPLAIN` over
   `EXPLAIN ANALYZE` on large tables.
5. In plan or read-only mode, do not connect to a non-local database. Write the query into the plan instead.
6. Put schema and data changes into versioned migrations. Run them on a local or disposable database first.
7. Never print connection strings or passwords. Read the host from the configuration, not the full DSN.

## Check

- `grep -rnE "load_dotenv|DATABASE_URL" <changed scripts>` → each match has a user approval in the session.
- No write or maintenance statement in a command that targets a non-local host.
- The agentic gate (`guard.db` in `.agent/gate.json`) blocks rule 2 and asks for rule 3.
