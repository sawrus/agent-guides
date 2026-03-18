---
name: feature-implementation-flow
type: workflow
trigger: /feature-impl
description: Implement a single feature into an existing full-stack service with strict layered architecture.
inputs:
  - feature_request
  - existing_codebase
outputs:
  - implemented_feature
  - passing_tests
roles:
  - pm
  - team-lead
  - designer
  - developer
  - qa
execution:
  initiator: pm
related-rules:
  - backend-architecture-rule.md
  - code-quality-guide.md
  - testing-ci-guide.md
uses-skills:
  - backend-developer
quality-gates:
  - layered architecture rules respected (no business logic in API layer)
  - unit and integration tests pass
  - lint and type checks pass
---

## Steps

### 1. Requirement Analysis & Models — `@pm` + `@team-lead`
- **Input:** feature request
- **Actions:** `@pm` captures requirements; `@team-lead` identifies impacted domain entities and determines if schema changes are needed; `@designer` provides UX/interaction specs if UI is involved
- **Output:** confirmed feature spec with data model notes
- **Done when:** impacted layers identified; `@developer` briefed

### 2. Design & Planning — `@team-lead` + `@designer`
- **Input:** confirmed feature spec
- **Actions:** design layer changes (models → repository → service → API); specify Pydantic/DTO schemas for input/output; plan Alembic migration if schema changes needed; define UX states (loading / empty / error / success) if frontend involved
- **Output:** brief implementation plan presented to `@pm` for user confirmation
- **Done when:** user/stakeholder confirms plan; approach is approved

### 3. Implementation — Inner to Outer — `@developer`
- **Input:** approved implementation plan
- **Actions:**
  - **Models/Schemas:** update `src/models/` (SQLAlchemy) if schema changes; create Alembic migration; define Pydantic input/output schemas in `src/schemas/`
  - **Repository Layer:** implement data access methods in `src/repositories/`; ensure IO-bound operations are async
  - **Service Layer:** implement business logic in `src/services/`; inject repository dependencies; handle exceptions, convert to business errors; do not import FastAPI/Flask objects here
  - **API Layer:** add/update endpoints in `src/api/`; validate input via schemas; call service methods only; no direct DB access
- **Output:** feature implemented on branch; no cross-layer violations
- **Done when:** all layers implemented; local checks pass

### 4. Verification — `@developer` + `@qa`
- **Input:** implemented feature branch
- **Actions:**
  - unit tests: test service logic (mock repositories); test repository logic (test DB or mocks)
  - integration tests: test API endpoints end-to-end with test client
  - `make lint` — zero errors; `make fmt` — no diffs; strict typing verified
  - `@qa` runs acceptance checks against feature spec
- **Output:** passing test suite; lint/type checks clean
- **Done when:** all checks pass; acceptance criteria verified

### 5. Review — `@team-lead`
- **Input:** feature branch + test results
- **Actions:** verify layer boundaries respected; check schema definitions and error handling; review test quality; provide blocking / non-blocking feedback
- **Output:** review feedback
- **Done when:** all blocking feedback resolved; `@team-lead` approves

### 6. Fix / Retest Loop — `@developer` + `@qa`
- **Input:** blocking feedback
- **Actions:** fix; re-run checks; re-request review
- **Done when:** zero blocking issues; all checks green

## Exit
`@team-lead` approval + passing checks = feature ready to merge.
