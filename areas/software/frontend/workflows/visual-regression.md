---
name: visual-regression
type: workflow
trigger: /visual-regression
description: Detect, triage, and resolve unintended UI visual diffs before release using snapshot comparison.
inputs:
  - changed_ui_scope
  - baseline_snapshots
outputs:
  - visual_diff_report
  - approved_or_rejected_baseline_update
roles:
  - developer
  - qa
  - designer
  - team-lead
execution:
  initiator: product-owner
related-rules:
  - quality.md
  - accessibility.md
  - performance.md
uses-skills:
  - testing-patterns
  - component-design
quality-gates:
  - critical diffs reviewed by designer before baseline update
  - accepted diffs documented with rationale
  - no unreviewed diffs merged
---

## Steps

1. Determine Visual Test Scope — `@product-owner` + `@developer`
- **Input:** changed UI components or routes
- **Actions:** identify which components and routes are affected by current changes; confirm baseline snapshots are up to date for the scope
- **Output:** test scope list
- **Done when:** scope defined; baseline verified

### 2. Run Capture & Comparison Suite — `@qa`
- **Input:** test scope
- **Actions:** run visual regression tool (Percy, Chromatic, Playwright snapshots) against current branch; generate diff images for all changed snapshots
- **Output:** visual diff report with diff images per component/route
- **Done when:** all diffs captured; report generated

### 3. Classify Diffs — `@designer` + `@qa`
- **Input:** visual diff report
- **Actions:** per diff: expected (intentional change matching design spec) vs. unexpected (unintended regression); `@designer` reviews all diffs involving design decisions; `@qa` flags unexpected diffs as blockers
- **Output:** classification per diff: approved / rejected / needs designer review
- **Done when:** all diffs classified; no diffs in "unknown" state

### 4. Fix or Approve Baseline Updates — `@developer` + `@designer`
- **Input:** classified diffs
- **Actions:** rejected (unexpected): `@developer` fixes the regression; approved (expected): update baseline snapshots with `@designer` explicit sign-off; document rationale for each approved baseline change
- **Output:** fixed code or updated baselines with documentation
- **Done when:** all rejected diffs fixed; all approved baselines updated with sign-off

### 5. Final Gate Decision — `@team-lead`
- **Input:** updated branch + baseline sign-offs
- **Actions:** verify all regressions fixed; confirm all approved baseline updates have designer sign-off; approve merge
- **Output:** merge approval
- **Done when:** all diffs resolved; no unreviewed changes

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /visual-regression"])
  role_1["product-owner"]
  role_2["developer"]
  role_3["qa"]
  role_4["designer"]
  role_5["team-lead"]
  step_1["1. Determine Visual Test Scope"]
  step_2["2. Run Capture & Comparison Suite"]
  step_3["3. Classify Diffs"]
  step_4["4. Fix or Approve Baseline Updates"]
  step_5["5. Final Gate Decision"]
  exit(["Zero unexpected diffs + all baseline updates designer-approved + @team-lead..."])
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
  role_3 -. owns .-> step_3
  role_2 -. owns .-> step_4
  role_4 -. owns .-> step_4
  role_5 -. owns .-> step_5
```
<!-- agent-diagram:end -->

## Exit
Zero unexpected diffs + all baseline updates designer-approved + `@team-lead` sign-off = visual review complete.
