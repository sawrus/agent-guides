---
description: Safety checks for running schema migrations against production databases.
trigger: manual
---

# Production migration runbook

- Use expand-and-contract for breaking schema changes: add the new column, dual-write, backfill, then remove the old column in a later release.
- Never rename or drop a column that the running application version still reads.
- Keep every migration compatible with the application version that runs before and after the deploy.
- Run the migration on staging with production-size data and record the execution time in the merge request.
- Take and verify a backup snapshot before running a production migration.
- Prepare and test the rollback SQL (or the down migration) before the production run.
- Use `CREATE INDEX CONCURRENTLY` on PostgreSQL tables over 1 million rows.
- Do not add a `NOT NULL` column with a volatile default to a large table in one statement; add it nullable, backfill, then add the constraint.
- Set `lock_timeout` (for example `SET lock_timeout = '5s'`) and `statement_timeout` in the migration session.
- Backfill data in batches of at most 10,000 rows with a pause between batches.
- Run migrations with the `migration_<service>` role from the CI job, not from a developer machine.
- Announce a maintenance window when the expected lock time exceeds 5 minutes.
