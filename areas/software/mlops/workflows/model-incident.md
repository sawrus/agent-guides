---
name: model-incident
type: workflow
trigger: /model-incident
description: Respond to a model degradation, drift, bias, or outage incident with structured triage, rollback, and postmortem.
inputs:
  - model_name
  - incident_type
outputs:
  - resolved_incident
  - postmortem
roles:
  - qa
  - developer
  - team-lead
execution:
  initiator: team-lead
agent: team-lead
related-rules:
  - production-safety.md
  - model-governance.md
  - data-integrity.md
uses-skills:
  - model-monitoring
  - model-evaluation
quality-gates:
  - rollback executed within 5 minutes for critical incidents
  - affected prediction window scoped and logged
  - postmortem published with monitoring improvement
---

## Steps

### 1. Immediate Response — `@team-lead`
- **Input:** incident alert
- **Actions:** assess impact (users affected? incorrect decisions made?); decide: tolerate degraded predictions or rollback NOW?; if critical → rollback to previous champion (< 5 min target)
- **Output:** rollback decision; incident severity classification
- **Done when:** system stabilized (rollback applied or consciously tolerated)

### 2. Diagnose — `@qa`
- **Input:** incident type
- **Actions:** drift → compare input distributions to training baseline (PSI); degradation → compare business metrics to post-deployment baseline; outage → check endpoint health, container logs, resource utilization; bias → compute fairness metrics for affected period
- **Output:** diagnosis report with evidence
- **Done when:** root cause category identified

### 3. Scope Affected Predictions — `@developer`
- **Input:** diagnosis report
- **Actions:** identify time window of degradation; log which predictions were made during affected window; notify downstream systems consuming model output
- **Output:** affected prediction log; downstream teams notified
- **Done when:** full impact window documented

### 4. Root Cause & Remediation — `@developer`
- **Input:** affected window + diagnosis
- **Actions:** data drift → schedule retraining with `/train-experiment`; model rot → `/train-experiment` with recent data; infrastructure → fix pipeline, verify feature consistency; code bug → implement fix, run `/evaluate-model` before re-deploying
- **Circuit breaker:** the incident → `/train-experiment` → `/evaluate-model` → `/deploy-endpoint` chain may be traversed at most once automatically per incident; if the redeployed model breaches again, keep the endpoint rolled back and escalate to `@team-lead` for human review
- **Output:** remediation action taken
- **Done when:** root cause fixed; new model validated or pipeline restored

### 5. Post-Incident — `@team-lead`
- **Input:** resolved incident
- **Actions:** add monitoring rule to catch pattern earlier; write postmortem; update model card with known failure modes
- **Output:** postmortem at `docs/incidents/<date>-<model>-root-cause.md`; monitoring updated; model card updated
- **Done when:** postmortem reviewed; prevention measures in place

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /model-incident"])
  role_1["team-lead"]
  role_2["qa"]
  role_3["developer"]
  step_1["1. Immediate Response"]
  step_2["2. Diagnose"]
  step_3["3. Scope Affected Predictions"]
  step_4["4. Root Cause & Remediation"]
  step_5["5. Post-Incident"]
  exit(["System restored + postmortem published + monitoring improved = incident clo..."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> exit
  role_1 -. owns .-> step_1
  role_2 -. owns .-> step_2
  role_3 -. owns .-> step_3
  role_3 -. owns .-> step_4
  role_1 -. owns .-> step_5
```
<!-- agent-diagram:end -->

## Exit
System restored + postmortem published + monitoring improved = incident closed.

**Next:** /train-experiment — when retraining is the remediation (bounded by the Step 4 circuit breaker); otherwise terminal — no follow-up workflow.
