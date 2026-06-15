---
name: performance-audit
type: workflow
trigger: /performance-audit
description: Execute performance testing and turn findings into prioritized, actionable engineering work.
inputs:
  - target_endpoint_or_flow
  - test_type
  - slo_baseline
outputs:
  - performance_report
  - prioritized_remediation_plan
roles:
  - qa
  - developer
  - team-lead
  - pm
execution:
  initiator: qa
related-rules:
  - quality-gates.md
  - test-strategy.md
uses-skills:
  - performance-testing
  - api-testing
quality-gates:
  - SLO regressions explicitly identified vs. baseline
  - bottleneck root cause identified (not just symptom)
  - remediation actions assigned with priority
---

## Steps

### 1. Scenario Definition & Baseline Alignment — `@qa`
- **Input:** target, test type, SLO baseline
- **Actions:** define test scenarios (load / stress / soak / spike) matching production traffic patterns; confirm SLO baseline values (p50, p99 latency; error rate; throughput); align on success/failure thresholds with `@team-lead`
- **Output:** test plan with scenarios and thresholds
- **Done when:** `@team-lead` approves test plan

### 2. Load/Stress Execution & Monitoring Capture — `@qa`
- **Input:** approved test plan
- **Actions:** run load test; capture: latency percentiles (p50/p95/p99), error rate, throughput, saturation metrics (CPU, memory, DB connections); identify breaking point if stress test
- **Output:** raw performance metrics; test execution evidence
- **Done when:** all scenarios executed; metrics captured

### 3. Bottleneck Analysis & Fix Proposal — `@developer` + `@qa`
- **Input:** performance metrics
- **Actions:** identify bottleneck location: DB queries (EXPLAIN ANALYZE), service CPU, network, memory pressure; `@developer` proposes targeted fix per bottleneck; estimate improvement before implementing
- **Output:** bottleneck analysis with proposed fixes and estimates
- **Done when:** root cause per regression identified; fixes proposed

### 4. Prioritization & Delivery Planning — `@team-lead` + `@pm`
- **Input:** analysis with fix proposals
- **Actions:** prioritize fixes by SLO impact and effort; `@pm` schedules as engineering work items; produce `performance_report.md` with: scenario results vs. SLO, bottleneck analysis, remediation backlog with priority
- **Output:** `performance_report.md`; remediation backlog items created
- **Done when:** report complete; backlog items assigned

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /performance-audit"])
  role_1["qa"]
  role_2["developer"]
  role_3["team-lead"]
  role_4["pm"]
  step_1["1. Scenario Definition & Baseline Alignment"]
  step_2["2. Load/Stress Execution & Monitoring Capture"]
  step_3["3. Bottleneck Analysis & Fix Proposal"]
  step_4["4. Prioritization & Delivery Planning"]
  exit(["Published report + prioritized remediation plan + backlog items created = a..."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> exit
  role_1 -. owns .-> step_1
  role_1 -. owns .-> step_2
  role_2 -. owns .-> step_3
  role_1 -. owns .-> step_3
  role_3 -. owns .-> step_4
  role_4 -. owns .-> step_4
```
<!-- agent-diagram:end -->

## Exit
Published report + prioritized remediation plan + backlog items created = audit complete.
