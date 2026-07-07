---
name: develop-feature-fullstack
type: workflow
trigger: /develop-feature-fullstack
description: Implement a feature end-to-end in a full-stack Python/FastAPI project following the layered architecture.
inputs:
  - feature_description
  - acceptance_criteria
  - tech_stack
outputs:
  - working_feature_branch
  - tests_passing
  - pr_ready
roles:
  - team-lead
  - developer
  - qa
execution:
  initiator: team-lead
related-rules:
  - backend-architecture-rule.md
  - api-design-guide.md
  - domain-models-guide.md
  - database-migrations-guide.md
  - testing-ci-guide.md
uses-skills:
  - backend-developer
  - api-design-principles
quality-gates:
  - all tests pass (unit + integration + e2e)
  - no mypy/ruff errors
  - architecture layer boundaries respected (no cross-layer imports)
  - PR description includes test evidence
---

## Steps

### 1. Design — `@team-lead`
- **Input:** feature description, acceptance criteria
- **Actions:** clarify domain model changes; draft API contract (endpoint, request/response schema, error codes); identify DB schema changes needed; flag breaking changes
- **Output:** `docs/design/feature-<name>.md` — API contract + data model
- **Done when:** API contract approved — `@team-lead` sign-off recorded in the design doc

### 2. DB Model & Migration — `@developer`
- **Input:** `docs/design/feature-<name>.md`
- **Actions:** define/update SQLAlchemy models; generate Alembic migration (`alembic revision --autogenerate`); review migration file — check for unsafe operations (column rename, NOT NULL without default); run `alembic upgrade head`
- **Output:** migration file in `alembic/versions/`; updated `models/`
- **Done when:** `alembic upgrade head` succeeds; existing tests still pass

### 3. Repository Layer — `@developer`
- **Input:** updated models
- **Actions:** implement CRUD operations in `repositories/`; use `AsyncSession`; apply cursor-based pagination for list queries; write repository unit tests with transaction rollback isolation
- **Output:** `repositories/<entity>_repo.py` + tests
- **Done when:** repository tests pass; no business logic in repo layer

### 4. Service Layer — `@developer`
- **Input:** repository layer
- **Actions:** implement business logic in `services/`; enforce invariants; manage transactions (`async with session.begin()`); emit domain events if needed; write service unit tests with fake repository
- **Output:** `services/<entity>_service.py` + tests
- **Done when:** service tests pass; service imports only repository, not DB directly

### 5. API Endpoint — `@developer`
- **Input:** service layer, API contract from Step 1
- **Actions:** implement FastAPI endpoint in `api/v1/endpoints/`; validate inputs via Pydantic schemas; use FastAPI `Depends()` for auth + DB; apply correct HTTP status codes; write API integration tests
- **Output:** endpoint file + `schemas/<entity>.py` + integration tests
- **Done when:** endpoint matches contract from Step 1; auth + validation tested; `make lint` clean

### 6. Frontend / UI — `@developer`
- **Input:** API contract, acceptance criteria
- **Actions:** implement UI changes (component, page, server action); connect to API; handle loading/error/empty states; add `data-testid` for E2E selectors
- **Output:** updated `features/<name>/` directory
- **Done when:** feature visible and functional in dev; all states handled

### 7. QA & PR — `@qa` + `@team-lead`
- **Input:** complete implementation from steps 2–6 (feature branch)
- **Actions:** write/run E2E test covering acceptance criteria; run full test suite (`make test`); verify no ruff/mypy errors; create PR with: description, test evidence (output), design doc link
- **Output:** passing CI + PR ready for review
- **Done when:** `make test` green; `make lint` clean; PR submitted

### 8. Document & Version — `@developer`
- **Input:** merged PR from step 7
- **Actions:** update feature docs under `docs/<feature>/README.md`; add a user-facing entry to `CHANGELOG.md`; bump the project version in the version source
- **Output:** docs + CHANGELOG + version committed in the same change set
- **Done when:** docs, CHANGELOG, and version merged

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /develop-feature-fullstack"])
  role_1["team-lead"]
  role_2["developer"]
  role_3["qa"]
  step_1["1. Design"]
  step_2["2. DB Model & Migration"]
  step_3["3. Repository Layer"]
  step_4["4. Service Layer"]
  step_5["5. API Endpoint"]
  step_6["6. Frontend / UI"]
  step_7["7. QA & PR"]
  step_8["8. Document & Version"]
  exit(["Merged PR with passing CI, docs and CHANGELOG updated, version bumped. Feat..."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> step_6
  step_6 --> step_7
  step_7 --> step_8
  step_8 --> exit
  role_1 -. owns .-> step_1
  role_2 -. owns .-> step_2
  role_2 -. owns .-> step_3
  role_2 -. owns .-> step_4
  role_2 -. owns .-> step_5
  role_2 -. owns .-> step_6
  role_3 -. owns .-> step_7
  role_1 -. owns .-> step_7
  role_2 -. owns .-> step_8
  step_8 -. iterate if blocked .-> step_1
```
<!-- agent-diagram:end -->

## Iteration Loop
If review finds issues → return to relevant step (Step 2 for schema issues, Step 4 for logic issues, Step 5 for API issues). Maximum 3 return iterations; if issues remain open after the third, stop and escalate to `@team-lead` with the open blocker list for a scope or design decision.

## Exit
Merged PR with passing CI, docs and CHANGELOG updated, version bumped. Feature accessible in target environment.

**Next:** terminal — no follow-up workflow.
