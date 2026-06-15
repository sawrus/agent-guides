---
name: cost-audit
type: workflow
trigger: /cost-audit
description: Analyze cloud spend, identify waste, and generate actionable optimization recommendations with Terraform snippets.
inputs:
  - audit_period
  - account_scope
outputs:
  - cost_report
  - optimization_recommendations
roles:
  - qa
  - team-lead
execution:
  initiator: qa
related-rules:
  - cost-governance.md
  - immutability.md
uses-skills:
  - terraform-patterns
  - observability-setup
quality-gates:
  - all waste categories checked (EBS, EC2, ELB, S3, RDS)
  - recommendations include specific resource IDs and estimated savings
---

## Steps

### 1. Fetch Billing Data — `@qa`
- **Input:** audit period, account scope
- **Actions:** query AWS Cost Explorer for target period; group by: service, environment tag, team tag
- **Output:** billing data grouped by service and tag
- **Done when:** data fetched; groupings confirmed

### 2. Analyze Spend Patterns — `@qa`
- **Input:** billing data
- **Actions:** compare to same period last month; flag services with > 20% month-over-month increase
- **Output:** spend pattern analysis; anomalies flagged
- **Done when:** anomalies identified

### 3. Detect Waste — `@qa`
- **Input:** billing data + resource inventory
- **Actions:** check for: unattached EBS volumes (> 7 days); stopped EC2 instances with EBS; idle load balancers (< 1 req/min for 7 days); S3 buckets without Intelligent Tiering (> 10 GB); over-provisioned RDS (CPU < 10% for 30 days)
- **Output:** waste list with resource IDs and current monthly cost
- **Done when:** all waste categories checked

### 4. Generate Recommendations — `@team-lead`
- **Input:** waste list + anomalies
- **Actions:** per waste item: resource ID, current monthly cost, recommended action, estimated savings, Terraform snippet for the fix; prioritize by savings impact
- **Output:** prioritized recommendation list with Terraform snippets
- **Done when:** all waste items have actionable recommendations

### 5. Report — `@team-lead`
- **Input:** analysis + recommendations
- **Actions:** produce `cost_report.md`: executive summary (total spend vs. budget vs. last month), total identified savings opportunity, full recommendation list; share with engineering leads
- **Output:** `cost_report.md`
- **Done when:** report shared; owners assigned for top recommendations

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /cost-audit"])
  role_1["qa"]
  role_2["team-lead"]
  step_1["1. Fetch Billing Data"]
  step_2["2. Analyze Spend Patterns"]
  step_3["3. Detect Waste"]
  step_4["4. Generate Recommendations"]
  step_5["5. Report"]
  exit(["Published report + owners assigned for top recommendations = audit complete."])
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
  role_2 -. owns .-> step_5
```
<!-- agent-diagram:end -->

## Exit
Published report + owners assigned for top recommendations = audit complete.
