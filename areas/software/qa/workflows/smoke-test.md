---
name: smoke-test
type: workflow
trigger: /smoke-test
description: Rapid post-change validation of critical user and system paths after a deployment.
inputs:
  - target_environment
  - deployment_context
outputs:
  - smoke_result_summary
  - rollback_recommendation
roles:
  - qa
  - developer
  - team-lead
  - pm
execution:
  initiator: qa
agent: qa
related-rules:
  - quality-gates.md
  - test-strategy.md
  - test-data.md
uses-skills:
  - e2e-patterns
  - api-testing
quality-gates:
  - critical path checks complete within 15 minutes of deployment
  - any blocking failure escalated immediately with rollback recommendation
---

## Steps

### 1. Prepare Environment & Test Data — `@qa`
- **Input:** deployed environment
- **Actions:** confirm services responding; seed or verify required test data; confirm smoke suite targets correct environment (not staging vs. production mix)
- **Output:** environment ready; test data confirmed
- **Done when:** ready to execute in < 5 minutes of deployment

### 2. Run Critical Smoke Scenarios — `@qa`
- **Input:** ready environment
- **Actions:** execute smoke suite covering: authentication, core business action, key API endpoints, data read/write round-trip; capture evidence (response codes, screenshots, timing)
- **Output:** pass/fail per scenario; evidence captured
- **Done when:** all scenarios executed

### 3. Defect Triage & Fix — `@developer`
- **Input:** smoke failures (if any)
- **Actions:** `@qa` classifies failure: blocking (rollback) vs. non-blocking (monitor); if blocking → `@developer` assesses rollback vs. hotfix; if non-blocking → document and continue
- **Output:** triage decision per failure
- **Done when:** all failures triaged; rollback or hotfix decision made if needed

### 4. Operational Risk Assessment — `@team-lead`
- **Input:** triage results
- **Actions:** review blocking vs. non-blocking failure list; assess overall risk of keeping deployment live; confirm rollback decision if blocking failures present
- **Output:** risk assessment note
- **Done when:** go/no-go confirmed by `@team-lead`

### 5. Communicate Go/No-Go — `@pm` + `@qa`
- **Input:** risk assessment
- **Actions:** `@qa` produces `smoke_result_summary.md`; `@pm` communicates status to stakeholders; if rollback: trigger `/deploy-production` with previous version — at most one automatic rollback deploy per release; if the rolled-back version also fails smoke, halt all automatic deploys, escalate to `@team-lead`, and trigger `/service-incident`
- **Output:** `smoke_result_summary.md`; stakeholders informed
- **Done when:** all parties notified; action taken if needed

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /smoke-test"])
  role_1["qa"]
  role_2["developer"]
  role_3["team-lead"]
  role_4["pm"]
  step_1["1. Prepare Environment & Test Data"]
  step_2["2. Run Critical Smoke Scenarios"]
  step_3["3. Defect Triage & Fix"]
  step_4["4. Operational Risk Assessment"]
  step_5["5. Communicate Go/No-Go"]
  exit(["Go status + summary published = deployment validated. No-go + rollback trig..."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> exit
  role_1 -. owns .-> step_1
  role_1 -. owns .-> step_2
  role_2 -. owns .-> step_3
  role_3 -. owns .-> step_4
  role_4 -. owns .-> step_5
  role_1 -. owns .-> step_5
```
<!-- agent-diagram:end -->

## Exit
Go status + summary published = deployment validated. No-go + rollback triggered = trigger `/service-incident`.

**Next:** /service-incident — on no-go with rollback; otherwise terminal — no follow-up workflow.
