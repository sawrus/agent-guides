```
@workflow(backend-project-full-cycle)

project:
  name: fingerprint-pipeline
  source_dir: src

stack:
  language: Python 3.12
  framework: FastAPI
  database: PostgreSQL
  messaging: Kafka
  migrations: Alembic

business_logic: >
  Process visit events from Kafka, extract user fingerprints,
  persist them, and link fingerprints to project users.

constraints:
  unit_test_coverage: ">=70%"
  blackbox_tests:
    - e2e-test
    - svt-test
```