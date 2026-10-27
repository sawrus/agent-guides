---
description: Backup schedule, retention, encryption, restore tests, and alerts for production databases.
trigger: manual
---

# Database backup policy

- Enable continuous WAL archiving to object storage for point-in-time recovery of every production PostgreSQL database.
- Run a daily full backup in addition to WAL archiving.
- Keep WAL for 7 days, daily backups for 30 days, weekly backups for 3 months, and monthly backups for 1 year.
- Take a snapshot before every production migration and keep it until the next major release.
- Encrypt every backup at rest with KMS-managed keys (AES-256).
- Store backups in a different account or project than the database and enable object lock or versioning.
- Run a restore test into an isolated environment every week and record the restore time and a row-count check.
- Set RTO 30 min and RPO 15 min for tier 1 databases; set RTO 4 h and RPO 1 h for tier 2.
- Alert when no backup completed in the last 26 hours.
- Alert when a backup size differs from the 7-day average by more than 20 %.
- Alert when backup storage use exceeds 70 % of its quota.
