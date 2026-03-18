---
name: drift-remediation
type: workflow
trigger: /drift-check
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
  initiator: developer
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

## Exit
All drift classified + REMEDIATE resolved + INVESTIGATE escalated = drift cycle complete.
