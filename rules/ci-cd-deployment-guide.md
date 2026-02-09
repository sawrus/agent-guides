---
trigger: always_on
glob: ci-cd-deployment-guide
description: enforce testing, docker, and deployment standards
---

# CI/CD & Deployment Rule

**Rules:**

- Run unit/integration tests before merging.
- Automate migrations, version bumps, changelog updates.
- Implement build & deploy commands in the project's build system (e.g., Makefile).
- Use Docker/K8s for consistent environments.
- Docker setup must include Dockerfile and orchestration (e.g. docker-compose.yml) with all used services described.

**Violations:**

- Code merges bypass tests.
- Migration/version updates are manual.
- Deployment is environment-specific.
- Missing or incomplete Docker setup.
