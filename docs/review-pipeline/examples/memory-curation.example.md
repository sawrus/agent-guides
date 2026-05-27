# Memory Curation Report

## Summary

The task introduced a durable convention: post-task review specialists are optional and remain outside the mandatory
SDLC role matrix. That convention is likely to help future agent-system changes. Temporary test output, command logs,
and generated report examples should not be stored as memory. No automatic memory write is recommended without user or
orchestrator approval.

## Store

| Priority | Fact | Reason | Suggested memory text |
|---|---|---|---|
| High | `instruction_reviewer` and `memory_curator` are optional post-task specialists, not SDLC owners. | Prevents future role-boundary drift. | Agentic treats `instruction_reviewer` and `memory_curator` as optional post-task review specialists outside the mandatory SDLC role matrix. |
| Medium | Review artifacts use `.reviews/<task-id>/` or timestamp fallback. | Helps future tasks place reports consistently. | Post-task review reports should be written under `.reviews/<task-id>/`, or `.reviews/YYYY-MM-DD-HHMMSS/` when no task id exists. |

## Update

| Existing memory | Replace with | Reason |
|---|---|---|
| None | None | No stale memory was identified. |

## Merge

| Memory A | Memory B | Merged memory | Reason |
|---|---|---|---|
| None | None | None | No duplicate memory was identified. |

## Ignore

| Fact | Reason |
|---|---|
| Exact shell output from test runs | Temporary logs are low-value memory. |
| Generated example report wording | Generated code/docs examples should remain in files, not memory. |
| One-time task status | Current task state is transient. |

## Delete candidates

| Memory | Reason |
|---|---|
| None | No delete candidate was found. |

## Contradictions

| Memory | New information | Resolution |
|---|---|---|
| None | None | No contradiction found. |

## Final recommendation

Store count: 2
Update count: 0
Merge count: 0
Delete candidate count: 0
Memory quality score: 8/10
Store only the two durable conventions. Ignore logs, generated examples, and current task progress.
