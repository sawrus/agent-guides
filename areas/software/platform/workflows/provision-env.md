---
name: provision-env
type: workflow
trigger: /provision-env
description: Spin up a complete, isolated environment for a branch or initialize a standing environment using Terraform.
inputs:
  - target_environment
  - branch
outputs:
  - provisioned_environment
  - environment_url
roles:
  - team-lead
  - developer
  - qa
  - pm
execution:
  initiator: team-lead
agent: team-lead
related-rules:
  - immutability.md
  - cost-governance.md
  - reliability.md
uses-skills:
  - terraform-patterns
  - k8s-manifests
  - networking
quality-gates:
  - no unexpected destroy operations in plan for non-preview envs
  - cost delta within budget before apply
  - smoke tests pass against new environment
---

## Steps

### 1. Validate Prerequisites — `@team-lead`
- **Input:** environment type, branch
- **Actions:** check cloud credentials active; verify Terraform state backend accessible; confirm no active locks on target environment state
- **Output:** prerequisites confirmed
- **Done when:** no locks; credentials valid

### 2. Plan Infrastructure — `@developer`
- **Input:** validated prerequisites
- **Actions:** `terraform init -reconfigure`; `terraform plan -out=tfplan`; if destroyed resources > 0 in non-preview env → HALT, request manual approval
- **Output:** `tfplan` artifact; destroy count confirmed
- **Done when:** plan reviewed; no unexpected destroys

### 3. Estimate Cost — `@developer`
- **Input:** tfplan
- **Actions:** `infracost breakdown --path tfplan`; HALT if delta > $500/month for preview environments
- **Output:** cost estimate; approval if within budget
- **Done when:** cost within budget; `@team-lead` approves

### 4. Apply Infrastructure — `@developer`
- **Input:** approved plan + cost estimate
- **Actions:** `terraform apply tfplan`; capture all outputs (endpoints, ARNs)
- **Output:** infrastructure provisioned; outputs captured
- **Done when:** apply exits 0; all resources created

### 5. Configure DNS & Ingress — `@developer`
- **Input:** infrastructure outputs
- **Actions:** register subdomain: `<branch>.staging.mycompany.com`; wait for SSL certificate validation; verify HTTPS endpoint responds
- **Output:** DNS and SSL active; HTTPS confirmed
- **Done when:** HTTPS endpoint reachable

### 6. Seed & Smoke Test — `@qa`
- **Input:** running environment
- **Actions:** run database migrations; run smoke test suite against new environment
- **Output:** smoke test results; environment validated
- **Done when:** smoke tests pass; environment confirmed functional

### 7. Report — `@pm`
- **Input:** validated environment
- **Actions:** post environment URL to PR comment; include: all endpoints, credentials location, teardown command
- **Output:** environment URL published in PR
- **Done when:** team has access and teardown instructions

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /provision-env"])
  role_1["team-lead"]
  role_2["developer"]
  role_3["qa"]
  role_4["pm"]
  step_1["1. Validate Prerequisites"]
  step_2["2. Plan Infrastructure"]
  step_3["3. Estimate Cost"]
  step_4["4. Apply Infrastructure"]
  step_5["5. Configure DNS & Ingress"]
  step_6["6. Seed & Smoke Test"]
  step_7["7. Report"]
  exit(["Smoke tests green + URL published = environment ready for use."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> step_6
  step_6 --> step_7
  step_7 --> exit
  role_1 -. owns .-> step_1
  role_2 -. owns .-> step_2
  role_2 -. owns .-> step_3
  role_2 -. owns .-> step_4
  role_2 -. owns .-> step_5
  role_3 -. owns .-> step_6
  role_4 -. owns .-> step_7
```
<!-- agent-diagram:end -->

## Exit
Smoke tests green + URL published = environment ready for use.

**Next:** terminal — no follow-up workflow.
