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
  initiator: product-owner
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

1. Detect Drift — `@product-owner` + `@devops-engineer`
```bash
# Run plan across all components; capture exit code
# Exit 0 = no changes, Exit 2 = changes detected
terraform plan -var-file=terraform.tfvars -detailed-exitcode 2>&1 | tee drift-report.txt
echo "Exit code: $?"
```

### 2. Classify Findings — `@devops-engineer` + `@team-lead`

| Class | Criteria | Action |
|:---|:---|:---|
| `ACCEPT` | Documented exception in PR comment | Suppress; add to ignore list |
| `REMEDIATE` | Unintended config change | Terraform apply within 48h |
| `INVESTIGATE` | Unknown origin; IAM/SG/encryption changes | Treat as P1; audit access logs |

- Any change to: IAM policies, security groups, encryption settings → **automatic INVESTIGATE**

### 3. Remediate (if REMEDIATE class) — `@devops-engineer`
```bash
# Review plan again — confirm only expected changes
terraform plan -var-file=terraform.tfvars -out=remediation.plan
# Apply after team-lead approval
terraform apply remediation.plan
```

### 4. Investigate (if INVESTIGATE class) — `@devops-engineer` + security
- Open P1 incident
- Pull cloud provider audit logs (CloudTrail / GCP Audit Logs) for affected resource
- Identify who/what made the change and when
- Remediate AND file security incident report

### 5. Report — `@devops-engineer`
- Update `drift-log.md` with date, resources affected, classification, action taken

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /drift-remediation"])
  role_1["product-owner"]
  role_2["devops-engineer"]
  role_3["team-lead"]
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
  role_2 -. owns .-> step_1
  role_2 -. owns .-> step_2
  role_3 -. owns .-> step_2
  role_2 -. owns .-> step_3
  role_2 -. owns .-> step_4
  role_2 -. owns .-> step_5
```
<!-- agent-diagram:end -->

## Exit
All drift classified + REMEDIATE resolved + INVESTIGATE escalated = drift cycle complete.
