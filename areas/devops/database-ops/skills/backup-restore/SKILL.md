---
name: backup-restore
description: "Procedure to verify a PostgreSQL or MySQL backup by restoring it into a scratch instance, and to run a point-in-time restore. Use when you check backups, set up backup jobs, or must restore data."
---

# Backup verification and restore

A backup counts only after a restore from it succeeds. Work on a scratch instance unless the user asks for a
production restore.

## 1. Find the backup setup

1. Find the backup tool and schedule: `pgbackrest`, `wal-g`, `barman`, `pg_dump` cron jobs, a Kubernetes
   operator (CloudNativePG, Zalando), or a managed service snapshot.
2. Record the retention, the WAL or binlog archive location, and the encryption key location.
3. If no backup job exists, stop and tell the user. Do not create one without agreement on the storage target.

## 2. List the latest backups

```bash
pgbackrest --stanza=<name> info
wal-g backup-list --detail
aws rds describe-db-snapshots --db-instance-identifier <id> --query 'DBSnapshots[-3:]'
```

Check that the newest full backup is younger than the policy allows and that WAL archiving has no gap.

## 3. Restore into a scratch instance

1. Start an empty instance with the same major version as the source:
   `docker run -d --name restore-check -e POSTGRES_PASSWORD=check postgres:<major>`.
2. Restore the latest backup:
   - `pg_dump` custom format: `pg_restore --no-owner --dbname=<scratch-url> <file>.dump`.
   - pgBackRest: `pgbackrest --stanza=<name> --pg1-path=<scratch-data-dir> restore`.
   - WAL-G: `wal-g backup-fetch <scratch-data-dir> LATEST`, then start the server with recovery settings.
   - Managed service: restore the snapshot to a new instance name with a `restore-check-` prefix.
3. Time the restore. Compare it with the recovery time objective (RTO).

## 4. Check the restored data

1. Compare row counts of the largest tables with the source, within the backup age:
   `SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 10;`
2. Read the newest timestamp of a write-heavy table. The gap to the backup time is the real recovery point
   (RPO).
3. Run `SELECT count(*)` on one table per schema to force a full read of its pages.
4. If counts or timestamps are off, the backup fails. Report the gap and keep the scratch instance for analysis.

## 5. Point-in-time restore (incident)

1. Ask the user first: confirm the target time, the target instance, and that writes to it are stopped.
2. Restore to a new instance, never over the damaged one:
   `pgbackrest --stanza=<name> --type=time --target="<YYYY-MM-DD HH:MM:SS+00>" restore`.
3. Check the data with step 4 and let the user confirm before traffic moves.
4. Ask the user first before you switch the application connection string or copy rows back.

## 6. Clean up

- Delete the scratch instance and any restored snapshot copy.
- Record the restore duration, the measured RPO, and the backup id in the docs page of the database service.
