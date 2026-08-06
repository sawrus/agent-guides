---
name: new-model
type: workflow
trigger: /new-model
description: Scaffold a complete dbt model with SQL, documentation, tests, and lineage from requirements to validated output.
inputs:
  - model_name
  - layer
  - source_table
outputs:
  - dbt_model_sql
  - yaml_documentation
  - validated_model
roles:
  - pm
  - team-lead
  - developer
  - qa
execution:
  initiator: pm
agent: pm
related-rules:
  - schema-management.md
  - pipeline-integrity.md
  - data-governance.md
uses-skills:
  - data-modeling
  - dbt-patterns
  - quality-checks
quality-gates:
  - dbt compile passes with no errors
  - standard tests pass (unique/not_null on PK, relationships on FKs)
  - model documented with column descriptions
---

## Steps

### 1. Requirements Gathering — `@pm`
- **Input:** model request
- **Actions:** confirm model name (snake_case), target layer (staging / intermediate / mart), source table, business purpose, and key metrics or grain
- **Output:** confirmed model spec
- **Done when:** spec unambiguous; `@team-lead` briefed

### 2. Model Design — `@team-lead`
- **Input:** confirmed model spec
- **Actions:** determine grain and primary key; identify required joins and business logic; specify standard tests (unique, not_null, relationships, recency for time-series); review lineage impact using `/lineage-trace` if modifying shared tables
- **Output:** design note with grain, PK, test list, lineage notes
- **Done when:** design approved; no lineage conflicts

### 3. SQL & YAML Implementation — `@developer`
- **Input:** design note
- **Actions:**
  - staging: SELECT with column renaming, type casting, deduplication
  - intermediate: business logic JOIN template
  - mart: fact/dimension template with surrogate key and audit columns
  - generate YAML docs: model description, auto-detected columns, standard tests
- **Output:** `models/<layer>/<model_name>.sql` + `<model_name>.yml`
- **Done when:** SQL implemented; YAML complete with all columns described

### 4. Validation — `@qa`
- **Input:** model files
- **Actions:** `dbt compile --select <model_name>`; `dbt test --select <model_name> --empty`; compare compiled SQL against design; verify tests are sufficient for the grain and business rules
- **Output:** validation report; compiled SQL preview
- **Done when:** `dbt compile` and `dbt test` pass; `@qa` confirms test coverage adequate

### 5. Review & Merge — `@team-lead`
- **Input:** validated model
- **Actions:** review SQL logic, naming conventions, documentation completeness; approve or return with blocking feedback
- **Done when:** `@team-lead` approves; PR merged

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /new-model"])
  role_1["pm"]
  role_2["team-lead"]
  role_3["developer"]
  role_4["qa"]
  step_1["1. Requirements Gathering"]
  step_2["2. Model Design"]
  step_3["3. SQL & YAML Implementation"]
  step_4["4. Validation"]
  step_5["5. Review & Merge"]
  exit(["Passing dbt tests + complete YAML docs + @team-lead approval = model produc..."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> exit
  role_1 -. owns .-> step_1
  role_2 -. owns .-> step_2
  role_3 -. owns .-> step_3
  role_4 -. owns .-> step_4
  role_2 -. owns .-> step_5
```
<!-- agent-diagram:end -->

## Exit
Passing dbt tests + complete YAML docs + `@team-lead` approval = model production-ready.

**Next:** terminal — no follow-up workflow.
