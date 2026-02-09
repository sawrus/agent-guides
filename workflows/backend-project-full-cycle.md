---
name: backend-project-full-cycle
type: workflow
description: >
  Full backend project lifecycle workflow:
  planning → implementation → blackbox validation.
  Enforces strict phase separation and skill switching.
inputs:
  - project_name
  - project_dir
  - tech_stack
  - business_logic_description
outputs:
  - production_ready_service
related-rules:
  - project-setup-guide.md
  - code-quality-guide.md
  - env-settings-guide.md
  - testing-ci-guide.md
  - e2e-test-guide.md
  - svt-test-guide.md
  - ci-cd-deployment-guide.md
uses-skills:
  - prompt-project-planner
  - app-builder
  - blackbox-testing
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

1. **Define Tech Stack:**
   - Determine Language, Framework, Database, and Messaging system.
   - If not provided in input, ask user to select from available options.
2. Ask clarifying questions about **Architecture & Requirements**:
   - Event schema & boundaries
   - Domain entities & relationships
   - Idempotency & deduplication strategies
   - Storage models & access patterns
   - Failure handling & retries
   - Throughput expectations & scaling
3. Do NOT write code.
4. Do NOT inspect source files.
5. Structure output strictly according to `output.schema.md`.
6. Generate artifacts:
   - `artifacts/plan_<task_id>.md`
7. Include in the plan:
   - Module layout inside `src/` (adapted to selected language)
   - Applied rules
   - Selected skills
   - This workflow reference

End condition:

- Ask explicitly:

> “Is the plan approved and may I proceed to implementation?”

---

## 🧑‍💻 Phase 2 — Implementation

**Active skill:** `app-builder`

Entry condition:

- Plan is explicitly approved by the user.

Rules:

- Code ONLY in `src/` (or strictly equivalent for the language)
- Unit tests ONLY in `tests/`

Steps:

1. Implement backend logic using **Selected Tech Stack**:
   - Adhere to the defined architecture (e.g., Domain/Service/Repository layers).
   - Use strict typing and validation where applicable (e.g., Pydantic for Python, Interfaces for TS).
   - Implement database migrations for any schema changes.
   - Implement clear boundaries for external systems (e.g., Kafka consumers).
2. Cover all logic with unit tests.
3. Ensure:
   - Formatting & Linting → passed (using project-standard tools)
   - Test Coverage → meets project threshold (default ≥ 70%)

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
   ```
