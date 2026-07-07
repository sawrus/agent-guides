---
name: add-migration
type: workflow
trigger: /add-migration
description: Plan, implement, and validate safe schema migrations using expand/contract principles.
inputs:
  - schema_change_request
  - affected_services
outputs:
  - migration_artifacts
  - validation_report
roles:
  - pm
  - team-lead
  - developer
  - qa
execution:
  initiator: team-lead
related-rules:
  - data_access.md
  - architecture.md
  - testing.md
uses-skills:
  - database-modeling
  - troubleshooting
quality-gates:
  - forward migration validated on test DB
  - rollback or mitigation strategy documented
  - no blocking backward-compatibility risk for running services
---

## Steps

### 1. Risk & Compatibility Analysis — `@team-lead`
- **Input:** schema change request + list of affected services
- **Actions:**
  - classify change: non-breaking (add nullable column, add index) vs. breaking (rename/drop column, change type, add NOT NULL)
  - for breaking changes: require expand/contract — two-phase migration across separate deployments
  - identify all consumers of the affected table/column; confirm backward-compatibility window
  - document rollback plan or mitigation (feature flag, dual-read window)
- **Output:** migration strategy doc: phases, compatibility window, rollback plan
- **Done when:** strategy approved; no services will break on forward migration

### 2. Migration Implementation — `@developer`
- **Input:** approved migration strategy
- **Actions:**
  - write migration script (Alembic, Flyway, Liquibase, etc.) following project conventions
  - Phase 1 (expand): add new column/table as nullable or with default; keep old structure intact
  - ensure migration is idempotent and reversible (`upgrade` + `downgrade` both implemented)
  - update application code to write to both old and new structures during transition if needed
- **Output:** migration file + updated application code on feature branch
- **Done when:** migration runs cleanly on local test DB; `downgrade` also verified

### 3. Test DB Validation & Data Checks — `@qa`
- **Input:** migration file + test DB
- **Actions:**
  - run `upgrade` on a copy of the test DB; verify schema matches expected state
  - run `downgrade`; verify clean revert with no data loss
  - execute affected queries and check index usage (EXPLAIN ANALYZE)
  - validate row counts and data integrity on key tables post-migration
- **Output:** `validation_report.md` — migration results, query plans, data integrity checks
- **Done when:** both directions validated; no unexpected data loss or performance degradation

### 4. Review & Remediation Loop — `@team-lead` + `@developer`
- **Input:** validation report
- **Actions:** `@team-lead` reviews migration SQL and application changes; flags any issues; `@developer` fixes and re-runs validation
- **Output:** approved migration
- **Done when:** `@team-lead` approves; no open issues in validation report

### 5. Readiness Report — `@pm`
- **Input:** approved migration + validation report
- **Actions:** confirm deployment sequence (migrate before or after app rollout); document rollback command; note monitoring signals to watch post-deploy; if no PM is assigned, `@team-lead` performs this step
- **Output:** `migration_readiness.md` with deployment steps, rollback command, monitoring checklist
- **Done when:** ops/release team has everything needed to deploy safely

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /add-migration"])
  role_1["team-lead"]
  role_2["developer"]
  role_3["qa"]
  role_4["pm"]
  step_1["1. Risk & Compatibility Analysis"]
  step_2["2. Migration Implementation"]
  step_3["3. Test DB Validation & Data Checks"]
  step_4["4. Review & Remediation Loop"]
  step_5["5. Readiness Report"]
  exit(["Validated migration + readiness report + @team-lead approval = ready to dep..."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> exit
  role_1 -. owns .-> step_1
  role_2 -. owns .-> step_2
  role_3 -. owns .-> step_3
  role_1 -. owns .-> step_4
  role_2 -. owns .-> step_4
  role_4 -. owns .-> step_5
  step_5 -. iterate if blocked .-> step_1
```
<!-- agent-diagram:end -->

## Iteration Loop
If validation reveals data issues or compatibility risks → return to Step 1 for strategy revision. Maximum 2 returns to Step 1; a third validation failure halts the migration and escalates to `@team-lead` with the open issue list for a decision.

## Exit
Validated migration + readiness report + `@team-lead` approval = ready to deploy.

**Next:** terminal — no follow-up workflow.
