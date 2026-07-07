---
name: drift-remediation
type: workflow
trigger: /drift-remediation
description: Detect, classify, and remediate infrastructure drift between Terraform state and actual cloud state.
inputs:
  - environment
  - component (optional — specific module to check)
outputs:
  - drift_report
  - remediation_applied or deferred
roles:
  - devops-engineer
  - team-lead
execution:
  initiator: devops-engineer
related-rules:
  - immutability.md
  - iac-standards.md
uses-skills:
  - drift-detection
  - terraform-modules
quality-gates:
  - drift classified before any apply
  - INVESTIGATE drift treated as security incident
---

## Steps

### 1. Detect Drift — `@devops-engineer`
- **Input:** environment and optional component from trigger inputs
```bash
# Run plan across all components; capture exit code
# Exit 0 = no changes, Exit 2 = changes detected
terraform plan -var-file=terraform.tfvars -detailed-exitcode 2>&1 | tee drift-report.txt
echo "Exit code: $?"
```
- **Done when:** plan completes; `drift-report.txt` captured with exit code recorded

### 2. Classify Findings — `@devops-engineer` + `@team-lead`
- **Input:** `drift-report.txt` from step 1

| Class | Criteria | Action |
|:---|:---|:---|
| `ACCEPT` | Documented exception in PR comment | Suppress; add to ignore list |
| `REMEDIATE` | Unintended config change | Terraform apply within 48h |
| `INVESTIGATE` | Unknown origin; IAM/SG/encryption changes | Treat as P1; audit access logs |

- Any change to: IAM policies, security groups, encryption settings → **automatic INVESTIGATE**
- **Done when:** every finding assigned a class; classification list recorded for steps 3–4

### 3. Remediate (if REMEDIATE class) — `@devops-engineer`
- **Input:** REMEDIATE-classified findings from the step 2 classification list
```bash
# Review plan again — confirm only expected changes
terraform plan -var-file=terraform.tfvars -out=remediation.plan
# Apply after team-lead approval
terraform apply remediation.plan
```
- If `terraform apply` fails: stop and re-plan; maximum 2 re-plans, then escalate to `@team-lead` with the open blocker list
- **Done when:** remediation applied; follow-up plan shows no unexpected changes

### 4. Investigate (if INVESTIGATE class) — `@devops-engineer`
- **Input:** INVESTIGATE-classified findings from the step 2 classification list
- Trigger /incident-response (at most one automatic trigger per drift run; if the condition recurs, stop and escalate to a human decision)
- Engage `devops/devsecops` guidance if malicious drift is suspected
- Pull cloud provider audit logs (CloudTrail / GCP Audit Logs) for affected resource
- Identify who/what made the change and when
- Remediate AND file security incident report
- **Done when:** change origin identified; incident report filed

### 5. Report — `@devops-engineer`
- **Input:** classification and remediation/investigation outcomes from steps 2–4
- Update `docs/operations/drift-log.md` with date, resources affected, classification, action taken
- **Done when:** `docs/operations/drift-log.md` updated and committed

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /drift-remediation"])
  role_1["devops-engineer"]
  role_2["team-lead"]
  step_1["1. Detect Drift"]
  step_2["2. Classify Findings"]
  step_3["3. Remediate (if REMEDIATE class)"]
  step_4["4. Investigate (if INVESTIGATE class)"]
  step_5["5. Report"]
  exit(["All drift classified + REMEDIATE resolved + INVESTIGATE escalated = drift c..."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> exit
  role_1 -. owns .-> step_1
  role_1 -. owns .-> step_2
  role_2 -. owns .-> step_2
  role_1 -. owns .-> step_3
  role_1 -. owns .-> step_4
  role_1 -. owns .-> step_5
```
<!-- agent-diagram:end -->

## Exit
All drift classified + REMEDIATE resolved + INVESTIGATE escalated = drift cycle complete.

**Next:** terminal — no follow-up workflow.
