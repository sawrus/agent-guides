---
trigger: always_on
glob: testing-ci-guide
description: enforce unit, integration, and e2e testing with formatting and deployment checks
---

# Testing & CI Rule

**Rules:**

- Every new code file must have a corresponding unit test file.
- Run formatting & linting: `make format lint` → fix until passed.
- Run unit tests: `make test-cov` → coverage ≥70%. Add tests for positive/negative scenarios.
- Start dependent services: `make docker-up` → logs must be clean.
- Apply migrations: `make migrate` → no errors allowed.
- Develop blackbox e2e-test with input data → full API scenario must pass (make e2e-test)

**Violations:**

- Missing unit tests.
- Coverage <70%.
- Format/lint errors not fixed.
- Docker logs contain errors.
- Migrations fail.
- E2E test fails.
