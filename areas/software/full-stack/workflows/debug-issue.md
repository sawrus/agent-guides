---
name: debug-issue
type: workflow
trigger: /debug-issue
description: Systematically diagnose and fix a bug in a full-stack Python/FastAPI + Next.js application.
inputs:
  - issue_description
  - error_logs
  - reproduction_steps
outputs:
  - root_cause_identified
  - fix_implemented
  - regression_test_added
roles:
  - "@backend-dev"
  - "@qa-engineer"
  - "@team-lead"
execution:
  initiator: developer
related-rules:
  - backend-architecture-rule.md
  - testing-ci-guide.md
  - logging-observability-guide.md
uses-skills:
  - troubleshooting
  - observability
quality-gates:
  - bug reproducible before fix
  - regression test fails before fix, passes after
  - no mypy/ruff errors introduced
  - root cause documented
---

## Steps

### 1. Triage — `@backend-dev`
- **Input:** issue description, error logs, environment context
- **Actions:** classify severity (P1 data loss/outage, P2 functional break, P3 cosmetic); identify affected component from stack trace; check if reproducible in staging; check recent deploys and migrations that could have caused this
- **Output:** triage note — severity, affected layer, reproduction status
- **Done when:** severity assigned; reproduction path identified or deemed flaky

### 2. Reproduce — `@backend-dev`
- **Input:** triage note, reproduction steps
- **Actions:** write a failing test that demonstrates the bug (unit or integration); if E2E: write Playwright test; run test — **must fail** before any fix; if test cannot be written, document why
- **Output:** failing test committed to branch `fix/<issue-id>`
- **Done when:** test reproduces issue deterministically; committed

### 3. Root Cause Analysis — `@backend-dev`
- **Input:** failing test, code
- **Actions:** use `EXPLAIN ANALYZE` for slow/incorrect queries; check log correlation (`request_id`); trace data through layers (API → Service → Repository → DB); identify exact line/condition causing the bug
- **Output:** root cause comment in ticket + code location identified
- **Done when:** root cause statement: "Bug is caused by [specific condition] in [file:line]"

### 4. Fix — `@backend-dev`
- **Input:** root cause, failing test
- **Actions:** implement minimal fix; run regression test — **must now pass**; run full test suite to check for regressions; fix must be in the correct architectural layer (don't fix a service bug in the API layer)
- **Output:** fix committed; tests passing
- **Done when:** regression test green; full suite green; `make lint` clean

### 5. Review & Document — `@team-lead`
- **Input:** fix + tests
- **Actions:** review that fix addresses root cause not symptoms; verify regression test quality; update incident log if P1/P2; PR includes: root cause, fix rationale, test evidence
- **Output:** approved PR; root cause documented
- **Done when:** PR merged; postmortem note added for P1/P2 issues

## Iteration Loop
If fix reveals deeper root cause → return to Step 3 with updated understanding.

## Exit
Merged fix + regression test + root cause documented in ticket.
