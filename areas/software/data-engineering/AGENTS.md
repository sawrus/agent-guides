# Data Engineering — guidance index

## What this area covers

Data pipeline engineering: dbt model development, data warehouse schema management, orchestration (Airflow / Prefect), data quality checks, lineage governance, SQL optimization, streaming patterns, and PII-safe data handling.

## Guidance chain

1. Project `.agent/` baseline (`AGENTS.md` + `.agent/*`)
2. `.agent/rules/*` — always active
3. `.agent/rules/*` — load all for this spec
4. `.agent/skills/*/SKILL.md` — load only the skill matching the current task
5. `.agent/workflows/*` — load the workflow matching the triggered command

## Inherited from general

- SDLC methodology and handoff contracts
- Git / CI / lint and code style baselines

## Data-engineering-specific constraints

- PII data must never appear in development or test environments without explicit masking — no exceptions.
- Schema changes follow the expand/contract pattern; no breaking changes to published marts without a migration plan.
- Every pipeline has an idempotency guarantee: re-running produces the same result without duplication.
- Data quality checks are part of the pipeline, not an afterthought — failing checks block downstream runs.

## Spec map

```text
.agent/
├── rules/
│   ├── data-governance.md      ← data ownership, access tiers, retention policy
│   ├── pii-handling.md         ← classification, masking, pseudonymization requirements
│   ├── pipeline-integrity.md   ← idempotency, atomicity, failure recovery
│   └── schema-management.md    ← expand/contract, versioning, backward compatibility
├── skills/
│   ├── data-modeling/SKILL.md        ← dimensional modeling, Kimball, Data Vault
│   ├── dbt-patterns/SKILL.md         ← model structure, tests, macros, materializations
│   ├── lineage-governance/SKILL.md   ← column-level lineage, OpenLineage, catalog integration
│   ├── orchestration/SKILL.md        ← DAG design, SLA alerts, dependency management
│   ├── quality-checks/SKILL.md       ← Great Expectations, dbt tests, anomaly detection
│   ├── sql-optimization/SKILL.md     ← query plans, partitioning, clustering, cost
│   └── streaming-patterns/SKILL.md   ← Kafka, Flink, exactly-once semantics, watermarks
├── workflows/
│   ├── new-model.md               ← /new-model
│   ├── schema-migration.md        ← /schema-migration
│   ├── backfill-data.md           ← /backfill-data
│   ├── data-quality-incident.md   ← /data-quality-incident
│   └── lineage-trace.md           ← /lineage-trace
└── prompts/
    └── *.md
```

## Discovery patterns

- `.agent/rules/*.md`
- `.agent/skills/*/SKILL.md`
- `.agent/workflows/*.md`
- `.agent/prompts/*.md`
