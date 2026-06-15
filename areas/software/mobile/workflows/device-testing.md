---
name: device-testing
type: workflow
trigger: /device-testing
description: Execute tests on a real device farm matrix before release to catch device-specific failures.
inputs:
  - test_suite
  - platform
outputs:
  - device_test_matrix_report
  - release_recommendation
roles:
  - qa
  - team-lead
execution:
  initiator: qa
related-rules:
  - platform-compliance.md
  - performance-budget.md
uses-skills:
  - mobile-testing
quality-gates:
  - device matrix covers latest 2 OS versions per platform
  - critical tests pass on ≥ 80% of device matrix
---

## Steps

### 1. Select Device Matrix — `@qa`
- **Input:** platform (ios / android / all)
- **Actions:** iOS: latest 2 iOS versions × [iPhone SE, iPhone 15, iPad]; Android: latest 2 Android versions × [low-end, mid-range, high-end]
- **Output:** confirmed device matrix
- **Done when:** matrix defined; device farm slots available

### 2. Upload Build — `@developer`
- **Input:** device matrix
- **Actions:** upload IPA/APK to device farm (AWS Device Farm / BrowserStack)
- **Output:** build available on device farm
- **Done when:** upload confirmed; build ID recorded

### 3. Execute Test Suite — `@qa`
- **Input:** uploaded build + device matrix
- **Actions:** run Detox (or project test framework) test suite on all matrix devices; capture per device: video, screenshots, logs, performance metrics
- **Output:** raw test results per device
- **Done when:** all devices executed; evidence captured

### 4. Analyze Results — `@qa` + `@team-lead`
- **Input:** raw results
- **Actions:** flag device-specific failures (not present in emulator); check: layout issues, performance variations, permission dialog handling; classify: critical (blocks release) vs. minor (track); block release if critical tests fail on > 20% of device matrix
- **Output:** pass/fail matrix by device × test; failure screenshots with device context
- **Done when:** all failures classified; release recommendation made

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /device-testing"])
  role_1["qa"]
  role_2["developer"]
  role_3["team-lead"]
  step_1["1. Select Device Matrix"]
  step_2["2. Upload Build"]
  step_3["3. Execute Test Suite"]
  step_4["4. Analyze Results"]
  exit(["Device matrix report + explicit go/no-go = device testing complete."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> exit
  role_1 -. owns .-> step_1
  role_2 -. owns .-> step_2
  role_1 -. owns .-> step_3
  role_1 -. owns .-> step_4
  role_3 -. owns .-> step_4
```
<!-- agent-diagram:end -->

## Exit
Device matrix report + explicit go/no-go = device testing complete.
