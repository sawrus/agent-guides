# Workflow agent field

## User-facing behavior

Every workflow frontmatter now exposes the initiating role in two places:

```yaml
execution:
  initiator: product-owner
agent: product-owner
```

The top-level `agent` field supports consumers that select an agent directly from workflow metadata. Its value must
exactly match `execution.initiator`; `roles`, workflow steps, prompts, and generated interaction diagrams are unchanged.

## Acceptance criteria

- Every file under `areas/**/workflows/*.md` contains exactly one top-level `agent` field.
- `agent` exactly matches `execution.initiator` in every workflow.
- `areas/template/workflow.tmpl.md` includes both fields and documents their equality requirement.

## Operational constraints

- Keep `agent` at the YAML top level immediately after the `execution` block.
- Validate repository consistency with `make lint`, `make build`, and `make test`.
