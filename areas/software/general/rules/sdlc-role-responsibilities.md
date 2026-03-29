---
trigger: always_on
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
| `@designer` | UX quality, information architecture, interaction consistency |

---

## Mandatory Subagent Mapping

- When subagent execution is required for SDLC workflows, spawn exactly **one subagent per role**.
- Mandatory one-to-one mapping: `@product-owner`, `@pm`, `@team-lead`, `@developer`, `@qa`, `@designer`.
- **Role consolidation is forbidden** — assigning multiple SDLC roles to one subagent is a process violation.
- If a role's output is missing, execution **must stop** and request that role's output before continuing.

---

## SDLC Phase Ownership

| SDLC Phase | Primary owner(s) | Key outputs |
|:---|:---|:---|
| Requirements | `@product-owner`, `@pm` | Problem statement, acceptance criteria, scope decisions, explicit non-goals |
| Design | `@team-lead`, `@designer` | Implementation plan, UX brief, architecture notes, risk register |
| Implementation | `@developer` | Code changes, tests, `implementation_notes.md` |
| Verification | `@qa`, `@team-lead` | Test report, defect log, review feedback, go/no-go |
| Deployment | `@pm`, `@team-lead` | Go/no-go decision, rollout plan, rollback procedure |
| Maintenance | `@developer`, `@qa`, `@team-lead` | Incident fixes, postmortems, hardening backlog |

---

## Required Handoff Order

Phases must execute in this order when subagent execution is required. Do not skip or reorder without documented justification.

```
Requirements (@product-owner, @pm)
    ↓
Design (@team-lead, @designer)
    ↓
Implementation (@developer)
    ↓
Verification (@qa, @team-lead)
    ↓
Acceptance / Release (@product-owner, @pm)
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

**4. Verification → Acceptance / Release**
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
