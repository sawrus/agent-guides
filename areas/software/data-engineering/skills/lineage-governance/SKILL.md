---
name: lineage-governance
description: "Covers data lineage tracing in dbt, column-change impact assessment, and data catalog standards; use when tracing data origins, assessing the impact of schema changes, or managing the data catalog."
---

# Skill: Data Lineage & Governance

## When to load

When tracing data origins, assessing impact of schema changes, or managing data catalog.

## Lineage in dbt

```
dbt manifest.json contains full lineage graph.
Use: dbt ls --select +model_name (upstream)
     dbt ls --select model_name+ (downstream)
```

## Impact Assessment for Column Change

```
Before renaming/dropping a column:
1. dbt ls --select model_name+ → list all downstream models
2. Check dashboards/BI tools connected to those models
3. Check ML feature pipelines consuming the column
4. Estimate blast radius: N models, M dashboards affected

Migration approach for breaking changes:
Phase 1: Add new column alongside old column
Phase 2: Migrate downstream consumers to new column (coordinate with owners)
Phase 3: Mark old column deprecated in YAML docs
Phase 4 (after 30 days): Drop old column
```

## Data Catalog Standards

Every table in the warehouse must have:
- `description`: what the table represents (grain, one sentence)
- `owner`: team or person responsible
- `data_classification`: PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED
- `sla_freshness`: expected update frequency
- Column descriptions for all non-obvious fields
