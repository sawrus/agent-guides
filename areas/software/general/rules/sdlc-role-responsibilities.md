---
trigger: manual
glob: sdlc-role-responsibilities
description: Role matrix for SDLC responsibilities, handoffs, and decision rights across subagents
---

# SDLC Role Responsibilities Matrix

## Roles

| Handle | Owns |
|:---|:---|
| `@product-owner` | Value definition, scope, acceptance criteria, prioritization |
| `@pm` | Planning cadence, dependency/risk management, stakeholder communication |
| `@team-lead` | Technical strategy, architecture quality, engineering sign-off |
| `@developer` | Implementation, technical correctness, test coverage |
| `@qa` | Verification strategy, quality evidence, go/no-go recommendation |
| `@analyst` | Requirements analysis, scenarios, API/data contracts, testable acceptance criteria, UX states |
| `@devops-engineer` | CI/CD, infrastructure-as-code, deployment, observability (optional stage) |

`@pm` and `@analyst` are optional: involve them when the change needs delivery planning or requirements/contract analysis.
Post-task specialists `@instruction-reviewer` and `@memory-curator` are outside this matrix; see `REVIEW_PIPELINE.md`.

---

## Mandatory Subagent Mapping

- When subagent execution is required for SDLC workflows, spawn exactly **one subagent per role**.
- Mandatory one-to-one mapping for every role the workflow lists: `@product-owner`, `@team-lead`, `@developer`, `@qa`, plus `@pm`, `@analyst`, and `@devops-engineer` when involved.
- **Role consolidation is forbidden** — assigning multiple SDLC roles to one subagent is a process violation.
- If a role's output is missing, execution **must stop** and request that role's output before continuing.

---

## SDLC Phase Ownership

| SDLC Phase | Primary owner(s) | Key outputs |
|:---|:---|:---|
| Requirements | `@product-owner`, `@pm` | Problem statement, acceptance criteria, scope decisions, explicit non-goals |
| Design | `@team-lead`, `@analyst` | Implementation plan, analysis spec (incl. UX brief), architecture notes, risk register |
| Implementation | `@developer` | Code changes, tests, `implementation_notes.md` |
| Verification | `@qa`, `@team-lead` | Test report, defect log, review feedback, go/no-go |
| Deployment (optional) | `@devops-engineer`, `@team-lead` | Pipeline/IaC changes, rollout plan, rollback procedure, deployment evidence |
| Maintenance | `@developer`, `@qa`, `@team-lead` | Incident fixes, postmortems, hardening backlog |

---

## Required Handoff Order

Phases must execute in this order when subagent execution is required. Do not skip or reorder without documented justification.

```
Requirements (@product-owner, optional @pm, @analyst)
    ↓
Design (@team-lead, optional @analyst)
    ↓
Implementation (@developer)
    ↓
Verification (@qa, @team-lead)
    ↓
Deployment (optional @devops-engineer)
    ↓
Acceptance / Release (@product-owner)
    ↓
Post-task review (@instruction-reviewer + @memory-curator, read-only, when the workflow has a review hook)
```

---

## Handoff Contracts

Every handoff must include the following artifacts. A handoff without these items is **incomplete** — the receiving role must reject it and request the missing outputs.

**1. Requirements → Design**
- Acceptance criteria (specific, testable)
- Constraints and dependencies
- Explicit non-goals (what is out of scope)

**2. Design → Implementation**
- Architecture boundaries and layer constraints
- UX states (loading, error, empty, success, permission-denied)
- Risk controls and security requirements

**3. Implementation → Verification**
- Test run evidence (commands + results)
- Known limitations or deferred items
- Migration / release notes if behavior changed

**4. Verification → Deployment (optional)**
- Go recommendation with test evidence
- Required infrastructure, pipeline, and configuration changes
- Rollback expectations

**5. Verification / Deployment → Acceptance / Release**
- Blocking defect status (resolved / accepted with rationale)
- Residual risks with owner and mitigation
- Go / no-go recommendation with written rationale

---

## Definition of Done (Cross-team)

A delivery is complete only when **all** of the following are true:

- Acceptance criteria validated with evidence.
- No unresolved blocking defects.
- Required checks pass: lint / test / build / security as applicable.
- Documentation and operational notes updated for all changed behavior.
- Rollback plan documented and verified where applicable.

---

## Violations

The following are **process violations** that must be flagged immediately:

- Merging multiple SDLC roles into fewer subagents when subagent execution is required.
- Starting implementation before requirements and design handoffs are complete and confirmed.
- Issuing a go recommendation without written test evidence.
- Accepting a deliverable with unresolved blocking defects (without explicit, documented Product Owner acceptance).
- Committing infrastructure changes without a corresponding IaC commit.

## Codex JEV model preparation

For an enabled JEV runtime, coordinators prepare each concrete subagent assignment before encrypted transport: send goal, scope and complexity to the installed `hook.py --host codex --prepare-spawn` JSON interface using the current session/task IDs and a unique request ID. Copy the returned `spawn` object unchanged (`agent_type`, `task_name`, `model` when present, `fork_turns`) and add only the complete assignment; no other response field is a spawn argument. Prepared selections are exceptions to guidance that omits guessed model overrides. `agent_type` keeps user pins and canonical native profile restrictions. If no `spawn` is returned, keep native defaults and state that application is unconfirmed. If the hook denies a prepared launch, spawn once with native role defaults (no model), do not retry or prepare again for that launch, and report `recommendation_discarded` with its reason code. Do not add unsupported spawn arguments or alter permissions. Other hosts keep their existing native adapters.
