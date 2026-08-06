---
name: debug-issue-fullstack
type: workflow
trigger: /debug-issue-fullstack
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
  - developer
  - team-lead
execution:
  initiator: developer
agent: developer
related-rules:
  - backend-architecture-rule.md
  - testing-ci-guide.md
  - logging-observability-guide.md
uses-skills:
  - backend-developer
  - blackbox-test
quality-gates:
  - bug reproducible before fix
  - regression test fails before fix, passes after
  - no mypy/ruff errors introduced
  - root cause documented
---

## Steps

### 1. Triage — `@developer`
- **Input:** issue description, error logs, environment context
- **Actions:** classify severity (P1 data loss/outage, P2 functional break, P3 cosmetic); identify affected component from stack trace; check if reproducible in staging; check recent deploys and migrations that could have caused this
- **Output:** triage note — severity, affected layer, reproduction status
- **Done when:** severity assigned; reproduction path identified or deemed flaky

### 2. Reproduce — `@developer`
- **Input:** triage note, reproduction steps
- **Actions:** write a failing test that demonstrates the bug (unit or integration); if E2E: write Playwright test; run test — **must fail** before any fix; if test cannot be written, document why
- **Output:** failing test committed to branch `fix/<issue-id>`
- **Done when:** test reproduces issue deterministically; committed

### 3. Root Cause Analysis — `@developer`
- **Input:** failing test, code
- **Actions:** use `EXPLAIN ANALYZE` for slow/incorrect queries; check log correlation (`request_id`); trace data through layers (API → Service → Repository → DB); identify exact line/condition causing the bug
- **Output:** root cause comment in ticket + code location identified
- **Done when:** root cause statement: "Bug is caused by [specific condition] in [file:line]"

### 4. Fix — `@developer`
- **Input:** root cause, failing test
- **Actions:** implement minimal fix; run regression test — **must now pass**; run full test suite to check for regressions; fix must be in the correct architectural layer (don't fix a service bug in the API layer)
- **Output:** fix committed; tests passing
- **Done when:** regression test green; full suite green; `make lint` clean

### 5. Review & Document — `@team-lead`
- **Input:** fix + tests from step 4 (branch `fix/<issue-id>`)
- **Actions:** review that fix addresses root cause not symptoms; verify regression test quality; for P1/P2 write `docs/incidents/<date>-<issue-id>-root-cause.md`; PR includes: root cause, fix rationale, test evidence
- **Output:** approved PR; root cause documented
- **Done when:** PR merged; `docs/incidents/` entry committed for P1/P2 issues

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /debug-issue-fullstack"])
  role_1["developer"]
  role_2["team-lead"]
  step_1["1. Triage"]
  step_2["2. Reproduce"]
  step_3["3. Root Cause Analysis"]
  step_4["4. Fix"]
  step_5["5. Review & Document"]
  exit(["Merged fix + regression test + root cause documented in ticket (and docs/in..."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> exit
  role_1 -. owns .-> step_1
  role_1 -. owns .-> step_2
  role_1 -. owns .-> step_3
  role_1 -. owns .-> step_4
  role_2 -. owns .-> step_5
  step_5 -. iterate if blocked .-> step_1
```
<!-- agent-diagram:end -->

## Iteration Loop
If fix reveals deeper root cause → return to Step 3 with updated understanding. Maximum 2 returns; after the second, stop and escalate to `@team-lead` with the findings so far to decide between a deeper investigation task or a mitigation-only fix.

## Exit
Merged fix + regression test + root cause documented in ticket (and `docs/incidents/` for P1/P2).

**Next:** terminal — no follow-up workflow.
