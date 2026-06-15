---
name: lineage-trace
type: workflow
trigger: /lineage-trace
description: Visualize full data lineage and assess blast radius of a column or table change before executing it.
inputs:
  - target_column_or_table
  - direction
outputs:
  - lineage_diagram
  - impact_report
roles:
  - developer
  - team-lead
execution:
  initiator: developer
related-rules:
  - data-governance.md
  - schema-management.md
uses-skills:
  - lineage-governance
  - data-modeling
quality-gates:
  - all downstream models and dashboards identified
  - SLA-critical models in blast radius explicitly flagged
  - migration checklist produced for breaking changes
---

## Steps

### 1. Parse Target — `@developer`
- **Input:** target column or table, direction (upstream / downstream / both)
- **Actions:** identify table and optional column in warehouse catalog; load dbt `manifest.json` for lineage graph
- **Output:** confirmed target node in lineage graph
- **Done when:** target resolved; manifest loaded

### 2. Trace Lineage — `@developer`
- **Input:** lineage graph
- **Actions:** upstream: walk `ref()` dependencies to source tables; downstream: walk all models that `ref()` the target; for column-level: identify all downstream `SELECT` statements referencing the column
- **Output:** upstream and downstream node lists
- **Done when:** full graph traversal complete

### 3. Impact Assessment — `@team-lead`
- **Input:** node lists
- **Actions:** for rename/drop: count downstream models and dashboards referencing the column; flag SLA-critical models; estimate migration effort (S/M/L)
- **Output:** impact summary — N models, M dashboards, criticality flags
- **Done when:** all impacted assets identified; `@team-lead` reviewed

### 4. Generate Report — `@developer`
- **Input:** impact assessment
- **Actions:** produce Mermaid diagram of lineage graph; write summary: affected models count, dashboard list, SLA-critical flags; produce migration checklist for breaking changes; for breaking: propose versioned approach if needed
- **Output:** `lineage_report.md` with diagram, summary, and checklist
- **Done when:** report reviewed and ready to share with affected owners

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /lineage-trace"])
  role_1["developer"]
  role_2["team-lead"]
  step_1["1. Parse Target"]
  step_2["2. Trace Lineage"]
  step_3["3. Impact Assessment"]
  step_4["4. Generate Report"]
  exit(["Published lineage report + migration checklist = ready to plan the change s..."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> exit
  role_1 -. owns .-> step_1
  role_1 -. owns .-> step_2
  role_2 -. owns .-> step_3
  role_1 -. owns .-> step_4
```
<!-- agent-diagram:end -->

## Exit
Published lineage report + migration checklist = ready to plan the change safely.
