---
name: backend-project-full-cycle
type: workflow
trigger: /backend-project-full-cycle
description: Full backend project lifecycle — planning → implementation → blackbox validation — for a greenfield service.
inputs:
  - project_name
  - project_dir
  - tech_stack
  - business_logic_description
outputs:
  - production_ready_service
roles:
  - pm
  - team-lead
  - developer
  - qa
execution:
  initiator: team-lead
agent: team-lead
related-rules:
  - project-guide.md
  - backend-architecture-rule.md
  - code-quality-guide.md
  - env-settings-guide.md
  - testing-ci-guide.md
  - e2e-test-guide.md
uses-skills:
  - prompt-project-planner
  - app-builder
  - blackbox-test
quality-gates:
  - plan explicitly approved by user before any code is written
  - unit tests pass with coverage ≥ 70%
  - blackbox/e2e tests pass against running service
---

## Phase 1 — Planning

**Active skill:** `prompt-project-planner`  
**Owner:** `@pm` (gather requirements) → `@team-lead` (create architecture plan) → `@pm` (present to user)

### Step 1.1 — Define Tech Stack — `@team-lead`
- **Input:** business logic description
- **Actions:** confirm language, framework, database, messaging system; if not provided — ask user to select from available options
- **Output:** confirmed tech stack in plan header
- **Done when:** stack agreed upon with user

### Step 1.2 — Requirements Clarification — `@pm` + `@team-lead`
- **Input:** confirmed tech stack
- **Actions:** ask clarifying questions about: event schema & boundaries; domain entities & relationships; idempotency & deduplication strategies; storage models & access patterns; failure handling & retries; throughput expectations & scaling
- **Output:** answers documented in plan
- **Done when:** no open architecture questions

### Step 1.3 — Architecture Plan — `@team-lead`
- **Input:** clarified requirements
- **Actions:** produce plan following `output.schema.md` from `prompt-project-planner` skill; include: module layout inside `src/`, applied rules, selected skills, this workflow reference; do NOT write code
- **Output:** `docs/plans/plan_<task_id>.md`
- **Done when:** plan complete per schema

### Step 1.4 — Plan Approval — `@pm`
- **Input:** architecture plan
- **Actions:** present plan to user; explicitly ask: *"Is the plan approved and may I proceed to implementation?"*
- **Output:** explicit user approval
- **Done when:** user confirms approval in writing — do not proceed to Phase 2 without this

---

## Phase 2 — Implementation

**Active skill:** `app-builder`  
**Owner:** `@developer` (implement) → `@qa` (unit test) → `@team-lead` (review)

**Entry condition:** plan is explicitly approved by the user.

### Step 2.1 — Backend Logic — `@developer`
- **Input:** approved architecture plan
- **Actions:**
  - implement using selected tech stack; follow layered architecture (Domain / Service / Repository)
  - use strict typing and validation (Pydantic for Python, interfaces for TS, etc.)
  - implement DB migrations for all schema changes
  - implement clear boundaries for external systems (Kafka consumers, HTTP clients, etc.)
  - code ONLY in `src/`; tests ONLY in `tests/`
- **Output:** implemented backend logic on branch
- **Done when:** all planned modules implemented

### Step 2.2 — Unit Tests & Quality — `@developer` + `@qa`
- **Input:** implemented code
- **Actions:**
  - cover all business logic with unit tests
  - `make lint` — zero errors
  - `make test` — coverage ≥ 70%
- **Output:** green unit tests; lint clean
- **Done when:** coverage threshold met; no lint violations

### Step 2.3 — Code Review — `@team-lead`
- **Input:** implemented branch
- **Actions:** verify architecture plan followed; check layering, typing, error handling; approve or return with blocking feedback
- **Output:** review feedback
- **Done when:** all blocking feedback resolved; `@team-lead` approves

---

## Phase 3 — Blackbox Validation

**Active skill:** `blackbox-test`  
**Owner:** `@qa` (execute) → `@team-lead` (review results)

**Entry condition:** unit tests are green; `@team-lead` has approved Phase 2.

### Step 3.1 — E2E Validation — `@qa`
- **Input:** approved service code
- **Actions:**
  - start services via Docker: `docker compose up`
  - execute real API calls against running service
  - validate full business flows end-to-end
  - run: `make e2e-test`
  - do not duplicate unit test logic — test observable behavior only
- **Output:** E2E test results; `make e2e-test` exit code 0
- **Done when:** all E2E scenarios pass

### Step 3.2 — Results Review & Report — `@team-lead` + `@pm`
- **Input:** E2E results
- **Actions:** `@team-lead` reviews test coverage and quality signal; `@pm` produces final delivery report; add a `CHANGELOG.md` entry and bump the project version
- **Output:** `docs/delivery/delivery_report_<task_id>.md` — plan vs. delivered, test evidence, known gaps
- **Done when:** `@team-lead` signs off; report complete; `CHANGELOG.md` and version bump committed

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /backend-project-full-cycle"])
  role_1["team-lead"]
  role_2["pm"]
  role_3["developer"]
  role_4["qa"]
  step_1["1.1 — Define Tech Stack"]
  step_2["1.2 — Requirements Clarification"]
  step_3["1.3 — Architecture Plan"]
  step_4["1.4 — Plan Approval"]
  step_5["2.1 — Backend Logic"]
  step_6["2.2 — Unit Tests & Quality"]
  step_7["2.3 — Code Review"]
  step_8["3.1 — E2E Validation"]
  step_9["3.2 — Results Review & Report"]
  exit(["Green E2E tests + @team-lead sign-off + delivery report = production-ready..."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> step_6
  step_6 --> step_7
  step_7 --> step_8
  step_8 --> step_9
  step_9 --> exit
  role_1 -. owns .-> step_1
  role_2 -. owns .-> step_2
  role_1 -. owns .-> step_2
  role_1 -. owns .-> step_3
  role_2 -. owns .-> step_4
  role_3 -. owns .-> step_5
  role_3 -. owns .-> step_6
  role_4 -. owns .-> step_6
  role_1 -. owns .-> step_7
  role_4 -. owns .-> step_8
  role_1 -. owns .-> step_9
  role_2 -. owns .-> step_9
  step_9 -. iterate if blocked .-> step_1
```
<!-- agent-diagram:end -->

## Iteration Loop
Phase 2 Steps 2.1–2.3 repeat until `@team-lead` approves (maximum 3 revision cycles). Phase 3 failure loops back to Phase 2 for fixes (maximum 2 returns). Exceeding either bound stops the loop and escalates to `@product-owner` for a scope decision.

## Optional JEV skill

Read `settings.jev.enabled` in project `.agentic.json`. When true, load
`.agent/skills/jev/SKILL.md` and use its helper at the checkpoints below.
When false/absent, skip this section and execute the standard workflow.
JEV is advisory; all required roles, QA, architecture sign-off and acceptance
remain mandatory. Missing/uncertain answers return to the assigned role. Copy
the question objects from the skill’s `references/questions.json` and follow
its `references/checkpoints.md` packet/action contracts; do not improvise
weaker questions. Keep original request and agreed scope in every packet.

| Checkpoint | State and maintained question | Handling |
| --- | --- | --- |
| Before approving a plan or extending scope | Original request, agreed scope/non-goals, approval provenance and proposed work. Use `scope_alignment` when scope alignment is disputed. | `scope_change` sends additions separately to PO/stakeholder; `clarify` gathers the missing decision. No silent maintenance or new resources. Normal plan approval remains mandatory. |
| Before the first spawn of each role, including exploration and specialists | Separate scoped role task and available model capabilities/cost order. Use `routing`: “Choose the least expensive sufficient model tier for this role's exact task within the original request and agreed scope.” | Apply a confident supported model override, preserving user pins/permissions. Record requested/observed model and fallback. Existing agents keep their model on followups; unsupported hosts retain their configured model. |
| Developer verification handoff | One claim, independent current command/run/tree identity, scenario/assertion and results. Use `evidence_support` for semantic coverage after local checks. | `supported` hands evidence to QA; `contradicted` returns a concrete finding; `insufficient` asks QA for the missing scenario/assertion. Failed/stale/missing command evidence needs no API call. JEV cannot authenticate execution. |
| Disputed review finding | Finding ID, cited criterion/gate, impact and diff evidence. Use `review_blocker`. | TL retains severity/sign-off ownership; optional unrelated maintenance becomes a separate proposal. Known failed gates already block without JEV. |
| After fixes, before another loop | Blocker IDs, current diff, independently verified closures, attempt history, limit and new hypothesis. Use `loop_action`. | `continue` gives Developer a bounded new hypothesis and QA retest; `gather_evidence` requests reproduction; `replan` requires PO/TL approval; `escalate` sends history to owners. `complete` requires all existing gates; exhausted limits escalate locally. |
| Before final acceptance | Exact criterion plus independent QA scenarios/assertions, expected/actual outputs and tree identity. Use `acceptance_support` per criterion. | PO owns acceptance. Contradictions return to QA/Developer; insufficient proof requests the missing scenario. Batch independent criteria; never weaken a criterion to match implemented behavior. |
| After the successful post-task specialist pair | Observed run history, current docs/instructions and concrete proposals with id/source/target/owner/done_when. Use `process_effectiveness`, `review_action` and independent `followup_needed` per proposal. | Report effectiveness separately from selected next-task IDs. Explicitly state no followup or missing evidence. Include target/owner/done_when for each recommendation; do not auto-edit guidance/memory. Cost efficiency uses `cost_effectiveness` only with measured total costs and a comparable accepted baseline; otherwise record insufficient locally. |

Invoke once for unchanged checkpoint evidence; batch related atomic questions.
Treat Choice/Score confidence below the skill's advisory floor as uncertain.
Never rerun merely to obtain a favorable verdict. No JEV request occurs when
its flag is disabled or there is no semantic decision beyond a deterministic check.

## Post-task review

- **Coordinator:** `@team-lead` (`execution.initiator`).
- **When:** after successful acceptance/sign-off and docs, CHANGELOG, and version completion, before the final user response.
- **Actions:** load `REVIEW_PIPELINE.md` from the project root; hand the same bounded evidence packet to `instruction_reviewer` and `memory_curator` as read-only specialists outside SDLC `roles`.
- **Once only:** review the top-level task once; nested workflows/increments hand observations to the parent. Do not launch inside fix/retest loops or after failed/deferred delivery.
- **Output:** `.reviews/<task-id>/instruction-review.md`, `memory-curation.md`, and `summary.md` (timestamp fallback per protocol); link them in the final response.
- **Failure:** record unavailable/failed specialists and evidence limitations; do not block successful delivery or retry automatically. Recommendations only; apply changes in a separate requested task.

## Exit
Green E2E tests + `@team-lead` sign-off + delivery report = production-ready service.

**Next:** terminal — no follow-up workflow.
