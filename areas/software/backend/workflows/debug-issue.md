---
name: debug-issue
type: workflow
trigger: /debug-issue
description: Resolve backend defects with reproducible diagnosis, verified fix, and root cause documentation.
inputs:
  - incident_or_bug_report
  - logs_metrics_traces
outputs:
  - verified_fix
  - root_cause_summary
roles:
  - pm
  - team-lead
  - developer
  - qa
execution:
  initiator: pm
related-rules:
  - architecture.md
  - security.md
  - testing.md
uses-skills:
  - observability
  - troubleshooting
quality-gates:
  - issue reproducible before fix is written
  - fix verified by automated checks and regression test
  - root cause documented with prevention note
---

## Steps

### 1. Triage & Impact Classification — `@pm` + `@team-lead`
- **Input:** bug report or incident alert
- **Actions:** confirm business impact and affected users; classify severity (P0 critical / P1 high / P2 normal); assign owner; set expected resolution time
- **Output:** severity label + assigned owner + ETA in ticket
- **Done when:** severity agreed; `@developer` assigned and briefed

### 2. Reproduce & Isolate — `@developer`
- **Input:** bug report + logs/metrics/traces (use `observability` skill to query)
- **Actions:**
  - reproduce the issue in a local or staging environment — do not fix without reproducing first
  - narrow to the smallest reproducible case
  - identify the code path: which layer (API / service / repository / infra)?
  - check recent commits touching that area: `git log -p -- <file>`
- **Output:** confirmed reproduction steps + suspected root cause hypothesis
- **Done when:** issue reliably reproducible; root cause narrowed to a specific code area

### 3. Fix Implementation — `@developer`
- **Input:** reproduction + root cause hypothesis
- **Actions:**
  - write a failing regression test first (proves the bug exists)
  - implement the minimal fix that makes the test pass
  - check for related occurrences of the same pattern elsewhere in the codebase
  - run full test suite to confirm no regressions: `make test`
- **Output:** fix + regression test on feature branch; all tests passing
- **Done when:** regression test passes; full suite green; fix is minimal and safe

### 4. Verification & Regression Checks — `@qa`
- **Input:** fix branch
- **Actions:**
  - reproduce original issue with fix applied — confirm resolved
  - run regression test suite on affected module
  - perform exploratory checks on related functionality
  - verify fix in staging environment if P0/P1
- **Output:** `verification_report.md` — confirmed fix, regression results, env tested
- **Done when:** issue resolved in all tested environments; no new failures introduced

### 5. Technical Review & Closure — `@team-lead`
- **Input:** fix branch + verification report
- **Actions:** review fix for correctness and side effects; confirm root cause analysis is complete; check that regression test is sufficient; write or approve `root_cause_summary.md` with prevention note
- **Output:** `root_cause_summary.md` — what failed, why, how fixed, how to prevent
- **Done when:** `@team-lead` approves fix; root cause documented; ticket closed

## Exit
Merged fix + verified resolution + root cause documented = incident closed.
