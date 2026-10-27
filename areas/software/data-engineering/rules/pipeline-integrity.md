---
description: Idempotency, deduplication, failure, and environment isolation for batch and streaming pipelines.
paths:
  - "**/dags/**"
  - "**/pipelines/**"
  - "**/models/**/*.sql"
---

# Pipeline integrity

- Make every pipeline run idempotent: a rerun for the same input partition must produce the same output.
- Use natural keys with `MERGE` or `INSERT OVERWRITE` of the target partition to deduplicate writes.
- Fail the pipeline run on a data quality test failure; never skip the failed check.
- Add data tests (for example dbt `unique`, `not_null`, `relationships`) to every new model.
- Read the target database and schema from environment variables; never hardcode a production target.
- Do not point development or staging pipelines at production sinks.
- Declare the upstream sources of every model in its schema file so lineage stays complete.
