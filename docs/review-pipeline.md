# Review Pipeline

Agentic ships two optional post-task specialist agents:

- `instruction_reviewer`: reviews how instructions affected task execution.
- `memory_curator`: recommends long-term memory store, update, merge, ignore, and delete-candidate actions.

These agents are outside the mandatory SDLC role matrix. They do not replace `product-owner`, `pm`, `team-lead`,
`developer`, `qa`, `designer`, or `devops-engineer`.

## Guidance-mode integration

Agentic currently provides guidance and IDE agent definitions for the review pipeline. It does not run a generic
post-task review runner. The parent or orchestrating agent should call the specialists after task execution when the
task size and risk justify the extra review.

Small tasks may skip this pipeline.

```yaml
review_pipeline:
  enabled: true
  default:
    - qa
    - instruction_reviewer
    - memory_curator
  task_types:
    agent_system:
      - qa
      - instruction_reviewer
      - memory_curator
    docs:
      - instruction_reviewer
      - memory_curator
    code:
      - qa
      - instruction_reviewer
      - memory_curator
```

`tool_optimizer` may be added to `agent_system` tasks in projects that install such a role. This repository does not
ship a `tool_optimizer` role.

## Output files

When the orchestrating agent writes review artifacts, use this layout:

```text
.reviews/<task-id>/
├── instruction-review.md
├── memory-curation.md
└── summary.md
```

If the task id is unavailable, use a timestamp in `YYYY-MM-DD-HHMMSS` format, for example:

```text
.reviews/2026-05-26-153000/
```

The specialist agents only produce Markdown reports. They do not write memory automatically and do not create review
files unless the parent task explicitly grants file-writing scope.

Example reports live under `docs/review-pipeline/examples/`.

## Report boundaries

`instruction_reviewer` reviews instruction effects only:

- `AGENTS.md`, `MEMORY.md`, role prompts, workflows, and tool guidance
- instruction clarity, usefulness, conflicts, redundancy, and missing rules
- repeated search loops, unnecessary memory lookups, unnecessary MCP calls, and token/tool waste

It must not review code quality or product requirements.

`memory_curator` reviews memory hygiene only:

- durable project facts, conventions, workflows, decisions, constraints, and rationale
- duplicate, stale, contradictory, or low-value memory candidates
- store/update/merge/ignore/delete recommendations

It must not store temporary logs, one-time commands, transient errors, generated code, secrets, temporary URLs, noisy
debug output, or current task state.
