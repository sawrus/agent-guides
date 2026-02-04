---
trigger: always_on
glob: e2e-test-guide
description: enforce full blackbox end-to-end testing after code & unit tests
---

# Rule — E2E Test

**Purpose:** Verify all business logic in full scenarios.

- Launch services via Docker.
- Feed input data/files.
- Call APIs to run the complete workflow.
- Verify output matches expected results.
- Run via Makefile: `make e2e-test`.
- Must **not** be confused with unit tests.

**Violations:** Missing E2E test, logs contain errors, output incorrect.
