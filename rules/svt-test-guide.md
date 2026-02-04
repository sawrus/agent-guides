---
trigger: always_on
glob: svt-test-guide
description: enforce simultaneous user/system tests on simplified data
---

# Rule — SVT Test

**Purpose:** Verify system stability under concurrent usage.

- Run N users/systems on simple data.
- Simulate load (e.g., Locust for FastAPI).
- Check outputs and service logs.
- Run via Makefile: `make svt-test`.
- Must **not** be confused with unit tests.

**Violations:** Missing SVT test, logs contain errors, concurrency failures.
