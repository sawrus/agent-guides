---
name: store-submission
type: workflow
trigger: /store-submission
description: Submit a validated mobile release to App Store or Google Play with compliance check and post-release monitoring.
inputs:
  - platform
  - build_path
outputs:
  - store_submission
  - post_release_monitoring_plan
roles:
  - developer
  - qa
  - team-lead
execution:
  initiator: product-owner
related-rules:
  - platform-compliance.md
  - security-mobile.md
uses-skills:
  - app-store-prep
  - mobile-testing
quality-gates:
  - crash-free rate ≥ 99.5% in pre-release track
  - privacy labels match actual data collection
  - compliance checklist from app-store-prep skill completed
---

## Steps

1. Validate Build — `@product-owner` + `@qa`
- **Input:** build artifact
- **Actions:** confirm all quality gates passed; physical device tests passed; crash-free rate in pre-release track ≥ 99.5%; run `app-store-prep` skill compliance checklist
- **Output:** quality gate sign-off
- **Done when:** all gates passed; `@team-lead` approves

### 2. Prepare Metadata — `@developer`
- **Input:** approved build
- **Actions:** update release notes (localized if applicable); update screenshots if UI changed; update app description if features changed
- **Output:** updated store metadata
- **Done when:** metadata reflects current release

### 3. Compliance Check — `@team-lead`
- **Input:** metadata + build
- **Actions:** privacy labels match actual data collection; permission usage descriptions current; no undisclosed data sharing; verify age rating is correct
- **Output:** compliance sign-off
- **Done when:** all compliance items confirmed

### 4. Submit — `@developer`
- **Input:** compliance-approved build + metadata
- **Actions:** iOS: upload IPA via Transporter → submit for App Review (24–48h); Android: upload AAB to internal track → promote: internal → closed → production (20% initial rollout)
- **Output:** submission confirmation
- **Done when:** submission received by store

### 5. Monitor Post-Release — `@qa`
- **Input:** live release
- **Actions:** watch for rating spike (negative reviews may indicate regression); monitor crash-free rate for first 48 hours; respond to App Review feedback if rejection; escalate to `/crash-triage` if crash-free rate drops
- **Output:** post-release monitoring report (48h window)
- **Done when:** 48 hours stable; no new critical issues

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /store-submission"])
  role_1["product-owner"]
  role_2["qa"]
  role_3["developer"]
  role_4["team-lead"]
  step_1["1. Validate Build"]
  step_2["2. Prepare Metadata"]
  step_3["3. Compliance Check"]
  step_4["4. Submit"]
  step_5["5. Monitor Post-Release"]
  exit(["Submission live + stable 48h monitoring = release complete."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> exit
  role_1 -. owns .-> step_1
  role_2 -. owns .-> step_1
  role_3 -. owns .-> step_2
  role_4 -. owns .-> step_3
  role_3 -. owns .-> step_4
  role_2 -. owns .-> step_5
```
<!-- agent-diagram:end -->

## Exit
Submission live + stable 48h monitoring = release complete.
