---
trigger: always_on
glob: project-setup-guide
description: Ensure new projects have a standard Makefile
---

# Project Setup Rule

**Rules:**

- Every new project **must include a README.md**
- Every new project **must include a src directory** for code files:
- Every new project **must include a Makefile** with standard targets:
    - `install`, `run-service`, `test-unit`, `test-e2e`, `migrate`, `format`, `lint`
- Makefile should support local development, CI pipeline, and service startup
- Include documentation on how to run each target
- Ensure Makefile works out-of-the-box after project creation

**Violations:**

- Missing Makefile
- Makefile lacks required targets
- Makefile does not run commands correctly
