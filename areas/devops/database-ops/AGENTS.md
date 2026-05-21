# Database Operations — guidance index

## What this area covers

Operational database management: backup verification, performance tuning, migration safety, incident response, PostgreSQL and Redis operations. Focus is on production database reliability, not application-level ORM usage.

## Guidance chain

1. Project `.agent/` baseline
2. `.agent/rules/*` — load all
3. `.agent/skills/*/SKILL.md` — load only the skill matching the current task
4. `.agent/workflows/*` — load the workflow matching the triggered command

## Cross-cutting constraints

- **Backups are not optional** — every production database has a verified backup and a tested restore procedure.
- **Migrations are backward-compatible** — no breaking schema change without a multi-step rollout plan.
- **No production access without audit log** — all direct DB sessions in production are logged and justified.
- **Verify before restore** — backup integrity is tested on a schedule; untested backups are treated as non-existent.

## Spec map

```text
.agent/
├── rules/
│   ├── backup-policy.md         ← frequency, retention, offsite requirements
│   ├── access-control.md        ← least-privilege roles, audit logging, break-glass
│   └── migration-runbook.md     ← pre/post checks, rollback gates, zero-downtime patterns
├── skills/
│   ├── backup-restore/SKILL.md       ← pg_dump, WAL archiving, PITR, restore drills
│   ├── db-performance/SKILL.md       ← EXPLAIN ANALYZE, index design, vacuum, slow query
│   ├── migration-safety/SKILL.md     ← expand/contract pattern, lock avoidance, online DDL
│   ├── postgres-operations/SKILL.md  ← replication, failover, extensions, pg_stat_*
│   └── redis-operations/SKILL.md     ← persistence modes, eviction, cluster, keyspace audit
├── workflows/
│   ├── backup-verify.md    ← /backup-verify
│   └── db-incident.md      ← /db-incident
└── prompts/
    └── *.md
```

## Discovery patterns

- `.agent/rules/*.md`
- `.agent/skills/*/SKILL.md`
- `.agent/workflows/*.md`
- `.agent/prompts/*.md`
