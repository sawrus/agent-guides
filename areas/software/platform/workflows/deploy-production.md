---
name: deploy-production
type: workflow
trigger: /deploy-production
description: Execute a gated, observable production deployment with progressive rollout and automatic rollback on SLO breach.
inputs:
  - version
  - deployment_strategy
outputs:
  - deployed_version
  - deployment_report
roles:
  - team-lead
  - developer
  - qa
  - pm
execution:
  initiator: team-lead
agent: team-lead
related-rules:
  - reliability.md
  - security-posture.md
  - immutability.md
uses-skills:
  - ci-cd-pipelines
  - observability-setup
quality-gates:
  - no active P0/P1 incidents before deploy starts
  - canary passes error rate and latency SLOs
  - smoke tests pass against production post-deploy
---

## Steps

### 1. Pre-flight — `@team-lead`
- **Input:** version tag
- **Actions:** confirm version tag exists and CI passed; verify staging is healthy with same version; check active incidents — HALT if P0/P1 open; post to `#deployments`: "Deploying <version> to production"
- **Output:** pre-flight sign-off
- **Done when:** all checks pass; team notified

### 2. Canary (10% traffic) — `@developer`
- **Input:** pre-flight sign-off
- **Actions:** deploy new image to canary pod group; monitor 5 minutes:
  - error rate delta > 0.5% → AUTO-ROLLBACK
  - p99 latency delta > 500ms → AUTO-ROLLBACK
  - pod crash loops → AUTO-ROLLBACK
- **Output:** canary health metrics
- **Done when:** canary stable for 5 minutes

### 3. Progressive Rollout — `@developer`
- **Input:** healthy canary
- **Actions:** 25% → wait 2 min → 50% → wait 2 min → 100%; continue SLO monitoring at each step; rollback if any threshold breached
- **Output:** 100% traffic on new version
- **Done when:** full rollout complete with no SLO breaches

### 4. Post-Deploy Validation — `@qa`
- **Input:** fully deployed version
- **Actions:** run smoke test suite against production; verify key business metrics not degraded > 10%; confirm monitoring dashboards reflect new version baseline
- **Output:** smoke test results; metric comparison
- **Done when:** all smoke tests pass; metrics stable

### 5. Complete — `@pm`
- **Input:** validated deployment
- **Actions:** post success to `#deployments` and status page; if rollback was triggered — trigger `/service-incident` (preserve logs; postmortem is assigned there); do not auto-redeploy after a rollback — redeploy requires a human go decision
- **Output:** `deployment_report.md`
- **Done when:** team and stakeholders informed

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /deploy-production"])
  role_1["team-lead"]
  role_2["developer"]
  role_3["qa"]
  role_4["pm"]
  step_1["1. Pre-flight"]
  step_2["2. Canary (10% traffic)"]
  step_3["3. Progressive Rollout"]
  step_4["4. Post-Deploy Validation"]
  step_5["5. Complete"]
  exit(["Green smoke tests + stable metrics + deployment report = release complete."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> exit
  role_1 -. owns .-> step_1
  role_2 -. owns .-> step_2
  role_2 -. owns .-> step_3
  role_3 -. owns .-> step_4
  role_4 -. owns .-> step_5
```
<!-- agent-diagram:end -->

## Exit
Green smoke tests + stable metrics + deployment report = release complete.

**Next:** /service-incident — if rollback was triggered; otherwise terminal — no follow-up workflow.
