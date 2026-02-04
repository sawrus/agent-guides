---
name: backend-project-full-cycle
description: >
  Full backend project lifecycle workflow:
  planning → implementation → blackbox validation.
  Enforces strict phase separation and skill switching.

uses-skills:
  - prompt-project-planner
  - app-builder
  - blackbox-testing

enforced-rules:
  - project-setup-guide.md
  - code-quality-guide.md
  - env-settings-guide.md
  - testing-ci-guide.md
  - e2e-test-guide.md
  - svt-test-guide.md
  - ci-cd-deployment-guide.md
---

## 🎯 Workflow Goal

Deliver a production-ready backend service with:

- approved plan
- clean implementation
- full unit + blackbox test coverage

Skipping phases or rules is forbidden.

---

## 🧠 Phase 1 — Planning

**Active skill:** `prompt-project-planner`

Rules:

- Planning only, no code
- No implementation inspection

Steps:

1. Ask clarifying questions about:
    - event schema
    - domain entities
    - fingerprint definition
    - idempotency & deduplication
    - storage model
    - failure handling
    - throughput expectations
2. Do NOT write code.
3. Do NOT inspect source files.
4. Structure output strictly according to `output.schema.md`.
5. Generate artifacts:
    - `artifacts/plan_<task_id>.md`
6. Include in the plan:
    - module layout inside `src/`
    - applied rules
    - selected skills
    - this workflow reference

End condition:

- Ask explicitly:

> “Is the plan approved and may I proceed to implementation?”

---

## 🧑‍💻 Phase 2 — Implementation

**Active skill:** `app-builder`

Entry condition:

- Plan is explicitly approved by the user.

Rules:

- Code ONLY in `src/`
- Unit tests ONLY in `tests/`

Steps:

1. Implement backend logic using:
    - Python 3.12
    - FastAPI
    - Pydantic models
    - DSN-based settings
    - Alembic migrations
    - Kafka consumers with clear boundaries
2. Cover all logic with unit tests.
3. Ensure:
    - `make format lint` → passed
    - `make test-cov` → coverage ≥ 70%

Exit condition:

- All unit tests pass
- No rule violations detected

---

## 🧪 Phase 3 — Blackbox Validation

**Active skill:** `blackbox-testing`

Entry condition:

- Unit tests are green.

Rules:

- Blackbox only
- No unit-test logic duplication

### E2E Validation

Steps:

1. Start services via Docker.
2. Execute real API calls.
3. Validate full business flows.
4. Run:
   ```bash
   make e2e-test