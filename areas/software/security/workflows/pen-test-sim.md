---
name: pen-test-sim
type: workflow
trigger: /pen-test-sim
description: Run automated OWASP Top-10 penetration test simulation against a staging environment.
inputs:
  - target_url
  - scope
outputs:
  - pentest_report
  - remediation_list
roles:
  - qa
  - developer
  - team-lead
execution:
  initiator: team-lead
agent: team-lead
related-rules:
  - secure-coding.md
  - compliance-baseline.md
uses-skills:
  - sast-dast-interpretation
  - security-headers
quality-gates:
  - target confirmed as staging (never production)
  - all OWASP Top-10 categories evaluated
  - Critical/High findings have remediation assigned
---

## Steps

### 1. Scope Confirmation — `@team-lead`
- **Input:** target URL
- **Actions:** verify target is staging/preview — NEVER production; log test start time for audit correlation; confirm scope (OWASP Top-10 or custom)
- **Output:** scope confirmation logged
- **Done when:** target and scope confirmed; never production

### 2. Passive Recon — `@qa`
- **Input:** confirmed target
- **Actions:** ZAP spider to discover all endpoints; identify technologies via response headers; check `robots.txt`, `sitemap.xml`
- **Output:** endpoint inventory; technology fingerprint
- **Done when:** full endpoint map produced

### 3. Active Scanning — `@qa`
- **Input:** endpoint inventory
- **Actions:** A01 Broken Access Control: IDOR on all object endpoints; A02 Crypto Failures: SSL config and header policies; A03 Injection: SQLi and XSS probes on all inputs; A05 Security Misconfiguration: headers, error responses; A07 Auth Failures: rate limiting, brute force protection
- **Output:** raw findings per OWASP category
- **Done when:** all in-scope categories evaluated

### 4. Manual Checks — `@qa`
- **Input:** active scan results
- **Actions:** auth token in URL parameters?; password reset: token expiry and single-use?; mass assignment on PUT/PATCH endpoints?
- **Output:** manual check results
- **Done when:** manual checks complete

### 5. Report — `@team-lead`
- **Input:** all findings
- **Actions:** produce OWASP-format finding report; include per finding: severity, evidence (request/response), remediation, CVSS score; assign remediation owners for Critical/High
- **Output:** `pentest_report_<date>.md`; remediation assignments
- **Done when:** report reviewed; remediation owners assigned

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /pen-test-sim"])
  role_1["team-lead"]
  role_2["qa"]
  step_1["1. Scope Confirmation"]
  step_2["2. Passive Recon"]
  step_3["3. Active Scanning"]
  step_4["4. Manual Checks"]
  step_5["5. Report"]
  exit(["Published report + Critical/High findings assigned = pen-test complete."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> exit
  role_1 -. owns .-> step_1
  role_2 -. owns .-> step_2
  role_2 -. owns .-> step_3
  role_2 -. owns .-> step_4
  role_1 -. owns .-> step_5
```
<!-- agent-diagram:end -->

## Exit
Published report + Critical/High findings assigned = pen-test complete.

**Next:** terminal — no follow-up workflow.
