---
name: release-build
type: workflow
trigger: /release-build
description: Build, sign, validate, and upload a production-ready mobile release artifact for iOS and/or Android.
inputs:
  - platform
  - environment
  - version
outputs:
  - signed_release_artifact
  - smoke_test_evidence
roles:
  - developer
  - qa
  - team-lead
execution:
  initiator: developer
agent: developer
related-rules:
  - platform-compliance.md
  - security-mobile.md
  - performance-budget.md
uses-skills:
  - app-store-prep
  - mobile-testing
quality-gates:
  - no debug flags or dev endpoints in release build
  - Detox smoke tests pass on physical device
  - artifact hash verified before upload
---

## Steps

### 1. Version Validation — `@developer`
- **Input:** version string
- **Actions:** confirm semver format; increment build number (versionCode / CFBundleVersion); verify git tag does not already exist
- **Output:** version confirmed; git tag reserved
- **Done when:** version unambiguous; no tag conflicts

### 2. Environment Check — `@developer`
- **Input:** target environment (staging / production)
- **Actions:** correct `.env` file loaded (no dev endpoints); all required env vars populated; no debug flags set (`DEV=false`, `FLIPPER=false`, sentry set to production DSN)
- **Output:** environment validation passed
- **Done when:** zero dev/debug flags in release config

### 3. Build — `@developer`
- **Input:** validated environment
- **Actions:**
  - iOS: `cd ios && pod install`; `xcodebuild archive -scheme MyApp -configuration Release`; export IPA with production signing profile
  - Android: `./gradlew clean`; `./gradlew bundleRelease`; sign with release keystore (credentials from CI secrets)
  - if signing fails: verify certificates and provisioning profiles (validity, expiry, team ID); maximum 2 retries, then escalate to `@team-lead`
- **Output:** IPA (iOS) / AAB (Android) artifact
- **Done when:** build exits 0; artifact produced

### 4. Validate Build — `@qa`
- **Input:** build artifact
- **Actions:** install on physical device; run Detox smoke tests; verify: launch, login, core action, crash-free; confirm no dev/debug indicators visible in UI
- **Output:** smoke test evidence; device validation record
- **Done when:** all smoke tests pass on physical device

### 5. Upload & Report — `@developer` + `@team-lead`
- **Input:** validated artifact
- **Actions:** `@team-lead` reviews smoke evidence; `@developer` uploads to TestFlight (iOS) or Firebase App Distribution (Android); record artifact path with hash; notify QA and PM
- **Output:** artifact uploaded; hash recorded; team notified
- **Done when:** upload confirmed; team has TestFlight/App Distribution link

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /release-build"])
  role_1["developer"]
  role_2["qa"]
  role_3["team-lead"]
  step_1["1. Version Validation"]
  step_2["2. Environment Check"]
  step_3["3. Build"]
  step_4["4. Validate Build"]
  step_5["5. Upload & Report"]
  exit(["Signed artifact uploaded + smoke tests passed + @team-lead approval = relea..."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> exit
  role_1 -. owns .-> step_1
  role_1 -. owns .-> step_2
  role_1 -. owns .-> step_3
  role_2 -. owns .-> step_4
  role_1 -. owns .-> step_5
  role_3 -. owns .-> step_5
```
<!-- agent-diagram:end -->

## Exit
Signed artifact uploaded + smoke tests passed + `@team-lead` approval = release build complete.

**Next:** /store-submission — pass `build_path` (the uploaded artifact) as input.
