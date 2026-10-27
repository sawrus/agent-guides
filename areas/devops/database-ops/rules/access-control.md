---
description: Least-privilege database roles, credentials, pooling, and audit settings for service databases.
paths:
  - "**/migrations/**"
  - "**/*.sql"
  - "**/pgbouncer*.ini"
---

# Database access control

- Create one `app_<service>` role per service with only `SELECT`, `INSERT`, `UPDATE`, `DELETE` on its own tables.
- Create a separate `migration_<service>` role for DDL; never grant `CREATE`, `ALTER`, or `DROP` to the application role.
- Create `readonly_<service>` roles with `SELECT` only for reporting and support access.
- Never use `GRANT ALL` or grant `SUPERUSER` to an application or migration role.
- Store each service credential in a secret manager (Vault, cloud secret store); never share one password between services.
- Rotate database credentials at least every 90 days and after offboarding a person with database access.
- Connect applications through a connection pooler (`pgbouncer` in transaction mode) and set a pool size limit per service.
- Enable `pgaudit` (or the engine equivalent) for all DDL and role changes.
- Revoke `CREATE` on schema `public` from `PUBLIC` and put service tables in a named schema.
- Require TLS (`sslmode=verify-full`) in every client connection string.
