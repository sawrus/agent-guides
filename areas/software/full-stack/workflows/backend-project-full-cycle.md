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
  initiator: product-owner
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

1. Define Tech Stack — `@product-owner` + `@team-lead`
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
- **Output:** `artifacts/plan_<task_id>.md`
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
- **Actions:** `@team-lead` reviews test coverage and quality signal; `@pm` produces final delivery report
- **Output:** `artifacts/delivery_report_<task_id>.md` — plan vs. delivered, test evidence, known gaps
- **Done when:** `@team-lead` signs off; report complete

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /backend-project-full-cycle"])
  role_1["product-owner"]
  role_2["team-lead"]
  role_3["pm"]
  role_4["developer"]
  role_5["qa"]
  step_1["1. Define Tech Stack"]
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
  role_2 -. owns .-> step_1
  role_3 -. owns .-> step_2
  role_2 -. owns .-> step_2
  role_2 -. owns .-> step_3
  role_3 -. owns .-> step_4
  role_4 -. owns .-> step_5
  role_4 -. owns .-> step_6
  role_5 -. owns .-> step_6
  role_2 -. owns .-> step_7
  role_5 -. owns .-> step_8
  role_2 -. owns .-> step_9
  role_3 -. owns .-> step_9
  step_9 -. iterate if blocked .-> step_1
```
<!-- agent-diagram:end -->

## Iteration Loop
Phase 2 Steps 2.1–2.3 repeat until `@team-lead` approves. Phase 3 failure loops back to Phase 2 for fixes.

## Exit
Green E2E tests + `@team-lead` sign-off + delivery report = production-ready service.
