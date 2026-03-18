---
name: create-endpoint
type: workflow
trigger: /create-endpoint
description: Implement a new API endpoint with contract, security, and test coverage.
inputs:
  - endpoint_scope
  - api_contract
  - non_functional_requirements
outputs:
  - production_ready_endpoint
  - tests_and_review_evidence
roles:
  - product-owner
  - pm
  - team-lead
  - developer
  - qa
execution:
  initiator: product-owner
related-rules:
  - architecture.md
  - data_access.md
  - security.md
  - testing.md
uses-skills:
  - api-design
  - database-modeling
  - troubleshooting
quality-gates:
  - API contract approved before implementation
  - security checks passed (auth, input validation, rate limiting)
  - automated tests green
---

## Steps

### 1. Scope & Contract — `@product-owner` + `@pm`
- **Input:** endpoint request
- **Actions:** define HTTP method, path, request/response schema, error codes, auth requirements, non-goals
- **Output:** API contract doc or OpenAPI snippet in `docs/<feature>/api-contract.md`
- **Done when:** contract is unambiguous and approved

### 2. Architecture Review — `@team-lead`
- **Input:** API contract
- **Actions:** verify contract aligns with existing API conventions (per `api-design` skill); confirm data model impact; identify performance and security risks (N+1, injection surface, auth scope); approve or request changes
- **Output:** architecture approval + notes on risks
- **Done when:** `@team-lead` approves; implementation approach clear

### 3. Implementation — `@developer`
- **Input:** approved contract + architecture notes
- **Actions:**
  - update schemas/DTOs for input validation (Pydantic, Joi, etc.)
  - implement repository method if new DB query needed — check indexes
  - implement service layer logic with error handling and business rules
  - wire API layer: route, auth middleware, response serialization
  - do not put business logic in the API handler
- **Output:** endpoint implemented on feature branch
- **Done when:** endpoint handles all contract scenarios; no lint errors

### 4. Test Design & Execution — `@qa`
- **Input:** implemented endpoint + API contract
- **Actions:**
  - write integration tests covering: happy path, validation errors (400), auth errors (401/403), not-found (404), edge cases
  - verify input sanitization and auth enforcement manually
  - check response schema matches contract
- **Output:** test suite passing; `docs/<feature>/test_report.md`
- **Done when:** all contract scenarios tested and passing; security checks confirmed

### 5. Code Review & Sign-off — `@team-lead`
- **Input:** feature branch + test report
- **Actions:** verify layering rules respected; check error handling completeness; confirm observability (request logged, errors traced); provide feedback as blocking / non-blocking
- **Output:** review feedback (PR comments or `review_feedback.md`)
- **Done when:** all blocking comments resolved; `@team-lead` approves

### 6. Fix / Retest Loop — `@developer` + `@qa`
- **Input:** blocking feedback
- **Actions:** fix issues; re-run tests; re-request review
- **Output:** updated branch
- **Done when:** zero blocking issues; tests green

### 7. Acceptance — `@product-owner` + `@pm`
- **Input:** verified endpoint + test evidence
- **Actions:** `@product-owner` confirms endpoint meets business need; `@pm` records delivery notes
- **Output:** endpoint accepted; delivery note in `docs/<feature>/delivery_summary.md`
- **Done when:** `@product-owner` signs off

## Exit
Accepted endpoint + passing tests + `@team-lead` sign-off = ready to merge.
