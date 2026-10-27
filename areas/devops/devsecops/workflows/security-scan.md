---
name: security-scan
type: workflow
trigger: /security-scan
description: Scan code, dependencies, images, and IaC, triage the findings, and add the scans as pipeline gates.
inputs:
  - repository_or_image
  - scan_scope
outputs:
  - fixes
  - pipeline_gate
  - accepted_risks
selection:
  general: false
  use-when: "The request asks to run or add SAST, secret, dependency, container image or IaC scans, to triage scanner findings, or to produce an SBOM or signed image."
  avoid-when: "Designing or building the release pipeline itself; use the release pipeline workflow."
uses-skills:
  - secret-detection
  - sbom-supply-chain
related-rules:
  - shift-left-policy.md
  - container-security.md
  - policy-as-code.md
artifacts:
  - .gitlab-ci.yml
  - .github/workflows/*.yml
---

# Security scan

Example request: `/security-scan "payment-service v2.5.0 pre-release gate: semgrep, trivy fs and image, gitleaks, checkov"`

## Steps

### 1. Run the scans

- **Do:** run the scanners that match the scope from the repository root, with pinned versions:
  `semgrep scan --config auto`, `gitleaks detect --redact`, `trivy fs --severity HIGH,CRITICAL .`,
  `trivy image <image>@<digest>`, `checkov -d <iac-dir>`. Save machine output (`--format sarif` or `json`).
- **Done when:** each scanner exits and you have its findings count by severity.

### 2. Triage

- **Do:** for each `HIGH` or `CRITICAL` finding, check reachability and exposure and classify it:
  `fix-now`, `false-positive` (with evidence), or `accepted-risk` (with owner and expiry). For a leaked secret,
  follow `secret-detection`: rotate first, then remove.
- **Done when:** every high and critical finding has a class and a reason.

### 3. Fix

- **Do:** upgrade dependencies and base images, change code or IaC, and record each false positive in the
  scanner ignore file (`.semgrepignore`, `.trivyignore`, `.gitleaksignore`) with a reason and expiry.
- **Done when:** a re-run shows no unclassified `HIGH` or `CRITICAL` finding.

### 4. Gate the pipeline

- **Do:** add the scans as blocking jobs on merge requests, and add SBOM and image signing with
  `sbom-supply-chain`. Ask the user first before you change protected branch settings or production
  admission policies.
- **Done when:** a merge request with a new critical finding fails the pipeline, and the docs page lists the
  scanners, thresholds, and accepted risks.
