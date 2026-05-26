# Codex Subagent Execution Policy (STRICT)

You must follow this decision rule before doing any non-trivial work.

## 1. Task Classification

Classify the task as one of the following:

### Trivial task (do directly, no subagent)

A task is trivial only if all conditions are true:

- It can be completed in 3 steps or fewer.
- It does not require repository exploration, reading multiple files, planning, or design decisions.
- It does not need specialized review, verification, or cross-role coordination.

Examples:

- a one-line syntax fix
- a simple shell command
- a short explanation
- a tiny mechanical edit in one file

If any doubt remains, treat the task as non-trivial.

### Non-trivial task (must use a subagent)

Everything else is non-trivial.

## 2. Hard Rule

For non-trivial tasks:

- Do not begin direct execution before spawning a role-matched subagent.
- Delegate analysis, planning, review, verification, or implementation explicitly.
- Prefer read-only planning and review roles first when the task is still ambiguous.

Skipping subagent usage is a policy violation.

## 3. Available Role Agents

Use the shipped role agents under `.codex/agents/`:

- `@product-owner` for scope, acceptance criteria, and final acceptance decisions
- `@pm` for delivery planning, milestones, risks, and dependency tracking
- `@team-lead` for architecture, quality gates, technical review, and sign-off
- `@designer` for UX flows, accessibility, and design-system consistency
- `@developer` for implementation, tests, and code delivery
- `@qa` for verification, test strategy, and go or no-go recommendations
- `@devops-engineer` for CI/CD, infrastructure, deployment safety, and observability

Optional post-task specialist agents:

- `@instruction_reviewer` for instruction effectiveness, tool discipline, memory discipline, ambiguity, and token-efficiency reports
- `@memory_curator` for long-term memory store/update/merge/ignore/delete-candidate recommendations

These specialist agents are not SDLC owners and do not replace the mandatory SDLC role mapping. Use them after
non-trivial task execution when instruction quality, memory hygiene, or future task performance needs review.

Role selection guidance:

- Prefer read-only agents for planning and review: `@product-owner`, `@pm`, `@team-lead`, `@designer`.
- Use writable execution agents only when needed: `@developer`, `@qa`, `@devops-engineer`.

## 4. Execution Flow

For non-trivial tasks:

1. Pick the role that best matches the current job.
2. Provide a clear objective, constraints, and expected output.
3. Wait for the result or use it to decide the next handoff.
4. Continue with the next role only after the current handoff is clear.

Suggested default flow:

1. `@product-owner` or `@pm` for scope and planning
2. `@team-lead` and `@designer` for technical and UX review
3. `@developer` or `@devops-engineer` for execution
4. `@qa` and `@team-lead` for verification and release readiness
5. Optional: `@instruction_reviewer` and `@memory_curator` for post-task review reports

When these optional specialists produce artifacts, use:

- `.reviews/<task-id>/instruction-review.md`
- `.reviews/<task-id>/memory-curation.md`
- `.reviews/<task-id>/summary.md`

If no task id exists, use a timestamp directory in `YYYY-MM-DD-HHMMSS` format.

## 5. Enforcement

If you start solving a non-trivial task without a subagent:

- stop immediately
- restart with a role-matched subagent

## 6. Priority

This policy overrides any default bias toward direct execution.

## 7. Goal

Maximize:

- decomposition
- delegation
- structured reasoning
- role clarity

Minimize:

- direct execution without planning
- context sprawl
- role overlap
