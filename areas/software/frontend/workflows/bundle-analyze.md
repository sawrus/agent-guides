---
name: bundle-analyze
type: workflow
trigger: /bundle-analyze
description: Analyze frontend bundle size impact and produce a prioritized optimization backlog.
inputs:
  - build_artifacts
  - baseline_metrics
outputs:
  - bundle_diff_report
  - optimization_backlog
roles:
  - developer
  - qa
  - team-lead
  - pm
execution:
  initiator: developer
agent: developer
related-rules:
  - performance.md
  - architecture.md
uses-skills:
  - performance-tuning
quality-gates:
  - budget regressions triaged with root cause
  - optimization actions prioritized by impact/effort
---

## Steps

### 1. Generate & Compare Bundle Metrics — `@developer`
- **Input:** build artifacts, baseline metrics
- **Actions:** run bundle analyzer (webpack-bundle-analyzer, vite-bundle-visualizer, source-map-explorer); compare current bundle sizes vs. baseline; flag any chunk exceeding performance budget; identify top contributors to size regression
- **Output:** bundle diff with size delta per chunk; budget violations flagged
- **Done when:** all chunks analyzed; violations identified

### 2. Validate Measurement Reliability — `@qa`
- **Input:** bundle metrics
- **Actions:** confirm measurement is reproducible (run analysis twice; results within 1%); verify build is production mode (no dev artifacts); confirm baseline was captured under same conditions
- **Output:** reliability confirmation or flag if measurements inconsistent
- **Done when:** measurements confirmed reliable

### 3. Prioritize Optimization Candidates — `@team-lead` + `@developer`
- **Input:** validated diff report
- **Actions:** rank candidates by: size impact × user impact × implementation effort; flag quick wins (unused imports, missing tree-shaking, large non-split chunks); flag strategic work (route-based code splitting, lazy-loaded components)
- **Output:** prioritized optimization list with effort estimates
- **Done when:** list reviewed; quick wins vs. strategic work separated

### 4. Publish Report & Next Actions — `@pm`
- **Input:** prioritized list
- **Actions:** produce `bundle_diff_report.md`: current vs. baseline sizes, budget violations, optimization backlog; schedule quick wins as engineering tasks; log strategic work in backlog
- **Output:** `bundle_diff_report.md`; backlog items created
- **Done when:** report shared; items logged in project tracker

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /bundle-analyze"])
  role_1["developer"]
  role_2["qa"]
  role_3["team-lead"]
  role_4["pm"]
  step_1["1. Generate & Compare Bundle Metrics"]
  step_2["2. Validate Measurement Reliability"]
  step_3["3. Prioritize Optimization Candidates"]
  step_4["4. Publish Report & Next Actions"]
  exit(["Report published + backlog items created = bundle analysis complete."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> exit
  role_1 -. owns .-> step_1
  role_2 -. owns .-> step_2
  role_3 -. owns .-> step_3
  role_1 -. owns .-> step_3
  role_4 -. owns .-> step_4
```
<!-- agent-diagram:end -->

## Exit
Report published + backlog items created = bundle analysis complete.

**Next:** terminal — no follow-up workflow.
