---
name: testing-ci-pipeline
type: workflow
trigger: /testing-ci-pipeline
description: Run the full CI and testing pipeline for backend or frontend projects and produce a verified quality signal.
inputs:
  - project_type
  - test_scope
outputs:
  - test_report
  - pipeline_status
roles:
  - developer
  - qa
  - team-lead
execution:
  initiator: product-owner
related-rules:
  - testing-ci-guide.md
  - code-quality-guide.md
uses-skills:
  - blackbox-test
quality-gates:
  - lint and format clean
  - all tests in selected scope pass
  - build artifact produced successfully
---

## Steps

1. Code Quality Check — `@product-owner` + `@developer`
- **Input:** current branch
- **Actions:** run linters and formatters using project-standard tools (e.g. `ruff` for Python, `eslint` + `prettier` for JS/TS); fix all errors — do not suppress
- **Output:** lint/format clean
- **Done when:** `make lint` exits 0; `make fmt` produces no diffs

### 2. Unit Tests — `@developer`
- **Input:** lint-clean branch
- **Actions:** run unit test suite: `make test`; confirm coverage meets project threshold (default ≥ 70%)
- **Output:** unit tests passing; coverage report
- **Done when:** `make test` exits 0; coverage threshold met

### 3. Build / Prepare — `@developer`
- **Input:** green unit tests
- **Actions:** build production artifact or Docker image (`make build` or `docker build`); confirm build succeeds with no warnings treated as errors
- **Output:** build artifact or image produced
- **Done when:** build exits 0; artifact is usable

### 4. E2E / Integration Tests — `@qa`
- **Input:** built artifact; condition: `test_scope` is `e2e` or `all`
- **Actions:** start services via Docker Compose; run blackbox/E2E suite: `make e2e-test`; capture logs and screenshots on failure
- **Output:** E2E test results; pass/fail per scenario
- **Done when:** all scenarios pass; or failures are classified (blocker vs. known flake)

### 5. Results Review & Report — `@team-lead` + `@qa`
- **Input:** all step outputs
- **Actions:** `@qa` produces `test_report.md` — step results, coverage delta, failure details; `@team-lead` reviews and makes pipeline pass/fail decision; blocker failures must be fixed before merge
- **Output:** `test_report.md`; pipeline status: PASS / FAIL / CONDITIONAL
- **Done when:** report complete; status communicated to `@developer`

## Failure Policy
If any step fails: pipeline halts. Fix the violation before proceeding. Do not skip or suppress failures.

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /testing-ci-pipeline"])
  role_1["product-owner"]
  role_2["developer"]
  role_3["qa"]
  role_4["team-lead"]
  step_1["1. Code Quality Check"]
  step_2["2. Unit Tests"]
  step_3["3. Build / Prepare"]
  step_4["4. E2E / Integration Tests"]
  step_5["5. Results Review & Report"]
  exit(["All steps green + test_report.md produced = pipeline passed."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> exit
  role_1 -. owns .-> step_1
  role_2 -. owns .-> step_1
  role_2 -. owns .-> step_2
  role_2 -. owns .-> step_3
  role_3 -. owns .-> step_4
  role_4 -. owns .-> step_5
  role_3 -. owns .-> step_5
```
<!-- agent-diagram:end -->

## Exit
All steps green + `test_report.md` produced = pipeline passed.
