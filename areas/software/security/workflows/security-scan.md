---
name: security-scan
type: workflow
trigger: /security-scan
description: Run a comprehensive security scan (SAST, deps, secrets, IaC) and produce a prioritized finding report.
inputs:
  - scan_scope
  - scan_mode
outputs:
  - finding_report
  - pr_review_comments
roles:
  - developer
  - team-lead
  - qa
execution:
  initiator: product-owner
related-rules:
  - secure-coding.md
  - dependency-policy.md
  - secrets-policy.md
uses-skills:
  - sast-dast-interpretation
  - dependency-audit
quality-gates:
  - no critical findings unaddressed before merge
  - high findings have 72-hour SLA assigned
  - secrets scan covers full git log (--full mode)
---

## Steps

1. SAST Scan — `@product-owner` + `@developer`
- **Input:** codebase
- **Actions:** `semgrep --config=p/security-audit`; `snyk code test`
- **Output:** SAST finding list
- **Done when:** scan complete; results saved

### 2. Dependency Audit — `@developer`
- **Input:** dependency files
- **Actions:** `npm audit --json` / `pip-audit` / `trivy fs`; cross-reference with OSV database; flag Critical (block) and High (plan) findings
- **Output:** dependency finding list with severity
- **Done when:** all deps scanned; Critical/High flagged

### 3. Secret Scanning — `@qa`
- **Input:** staged changes (PR mode) or full git log (full mode)
- **Actions:** `trufflehog filesystem` on staged changes; `gitleaks` on git log (last 100 commits if PR, full history if --full)
- **Output:** secret scan results
- **Done when:** no unreviewed secrets in scope

### 4. Infrastructure Scan — `@developer` (if IaC exists)
- **Input:** Terraform / K8s manifests
- **Actions:** `checkov -d terraform/`; `kube-score` on K8s manifests
- **Output:** IaC finding list
- **Done when:** all manifests scanned

### 5. Synthesize & Report — `@team-lead`
- **Input:** all scan results
- **Actions:** merge all findings; deduplicate by location; prioritize: Critical → High → Medium → Low; for Critical/High provide specific remediation code; post to PR as review comment; Critical → request changes (block merge); High → comment with 72-hour SLA; save full report: `.security/scan-results-<timestamp>.json`
- **Output:** `finding_report.md`; PR review comments
- **Done when:** report published; PR status set per findings

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /security-scan"])
  role_1["product-owner"]
  role_2["developer"]
  role_3["qa"]
  role_4["team-lead"]
  step_1["1. SAST Scan"]
  step_2["2. Dependency Audit"]
  step_3["3. Secret Scanning"]
  step_4["4. Infrastructure Scan"]
  step_5["5. Synthesize & Report"]
  exit(["No unaddressed Critical findings + report saved = scan complete."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> exit
  role_1 -. owns .-> step_1
  role_2 -. owns .-> step_1
  role_2 -. owns .-> step_2
  role_3 -. owns .-> step_3
  role_2 -. owns .-> step_4
  role_4 -. owns .-> step_5
```
<!-- agent-diagram:end -->

## Exit
No unaddressed Critical findings + report saved = scan complete.
