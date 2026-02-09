```yaml
# Workflow Trigger
workflow: backend-project-full-cycle

# Inputs
project_name: fingerprint-pipeline
project_dir: src

tech_stack:
  language: Python 3.12
  framework: FastAPI
  database: PostgreSQL
  messaging: Kafka
  migrations: Alembic

business_logic_description: >
  Process visit events from Kafka, extract user fingerprints,
  persist them, and link fingerprints to project users.

# Constraints (implicitly handled by rules, but good for context)
constraints:
  unit_test_coverage: ">=70%"
  blackbox_tests:
    - e2e-test
    - svt-test
```
