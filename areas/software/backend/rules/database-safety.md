---
description: Keep agents and scripts from changing a real database (production, replicas, shared stages).
paths:
  - "**/migrations/**"
  - "**/alembic/**"
  - "**/*.sql"
  - "**/db/**"
  - "**/scripts/**"
  - "**/.env.example"
---

# Database safety

- Treat any host other than `localhost`, `127.*`, `::1`, a unix socket, or `sqlite` as production; a replica counts.
- Hand `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `TRUNCATE`, `DROP`, `ALTER`, `CREATE INDEX`, `GRANT`, `REVOKE`,
  `COPY ... FROM`, `VACUUM`, `ANALYZE`, `REINDEX`, `CLUSTER`, `REFRESH MATERIALIZED VIEW`, and
  `pg_terminate_backend` for such a host to the user as text; do not execute them.
- Name the target host and the reason when you ask to use credentials from `load_dotenv`, `source .env`, or
  `DATABASE_URL`.
- Open a read-only session (`SET default_transaction_read_only = on`) and set `statement_timeout` for every query
  on such a host.
- Use `EXPLAIN` instead of `EXPLAIN ANALYZE` on tables with more than 1 million rows.
- Write the query into the plan instead of connecting when the host runs in plan or read-only mode.
- Put schema and data changes into versioned migrations and run them on a local or disposable database first.
- Print only the host and database name from a connection string; never print passwords or full DSNs.
- Keep `guard.db` in `.agent/gate.json` at its defaults (`write: deny`) unless the user changes it.
