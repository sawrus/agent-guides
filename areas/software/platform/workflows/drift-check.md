---
name: drift-check
type: workflow
trigger: /drift-check
description: Detect and report differences between IaC definitions and actual cloud state, with optional auto-remediation.
inputs:
  - target_environment
  - auto_fix
outputs:
  - drift_report
  - remediation_issues
roles:
  - qa
  - team-lead
  - developer
execution:
  initiator: qa
related-rules:
  - immutability.md
  - security-posture.md
uses-skills:
  - terraform-patterns
quality-gates:
  - Category D drift (unexpected destroy) pages on-call immediately
  - auto-fix applies only Category A (tag-only) drift
---

## Steps

### 1. Fetch Live State — `@qa`
- **Input:** target environment
- **Actions:** `terraform refresh` for target environment; ensure state backend is up to date
- **Output:** refreshed state
- **Done when:** state reflects current cloud reality

### 2. Compute Diff — `@qa`
- **Input:** refreshed state
- **Actions:** `terraform plan -detailed-exitcode`; exit code 2 = drift detected; capture full diff output
- **Output:** diff report
- **Done when:** drift computed; exit code recorded

### 3. Classify Drift — `@team-lead`
- **Input:** diff report
- **Actions:** A: tag-only drift → auto-fixable, low risk; B: config drift → review required; C: missing resource (created manually) → investigate origin; D: unexpected destroy → CRITICAL, page on-call immediately
- **Output:** drift classification per item
- **Done when:** all drift items classified

### 4. Report — `@team-lead`
- **Input:** classified drift
- **Actions:** post summary to Slack `#infra-alerts`; Category D → page on-call immediately, do not wait
- **Output:** Slack notification; on-call paged if D
- **Done when:** team informed

### 5. Remediate — `@developer` (if `--fix` flag)
- **Input:** classified drift
- **Actions:** auto-apply Category A only: `terraform apply -target=<resource>`; for B/C/D: create GitHub issue, assign to IaC owner; do NOT auto-apply B/C/D
- **Output:** Category A drift resolved; issues created for B/C/D
- **Done when:** Category A applied; B/C/D tracked in issues

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /drift-check"])
  role_1["qa"]
  role_2["team-lead"]
  role_3["developer"]
  step_1["1. Fetch Live State"]
  step_2["2. Compute Diff"]
  step_3["3. Classify Drift"]
  step_4["4. Report"]
  step_5["5. Remediate"]
  exit(["Drift report published + Category A resolved (if --fix) + B/C/D tracked = d..."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> exit
  role_1 -. owns .-> step_1
  role_1 -. owns .-> step_2
  role_2 -. owns .-> step_3
  role_2 -. owns .-> step_4
  role_3 -. owns .-> step_5
```
<!-- agent-diagram:end -->

## Exit
Drift report published + Category A resolved (if --fix) + B/C/D tracked = drift check complete.
