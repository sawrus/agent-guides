# Centralized guidance loading and memory writes

## User-facing behavior

Agent guidance loading rules are defined in the root `AGENTS.md` instead of being repeated in each `areas/**/AGENTS.md` specialization index. Area files now focus on scope, inherited constraints, overrides, and spec maps.

`MEMORY.md` now explicitly tells agents to use `mempalace_store` proactively for durable project facts when those facts are discovered, decided, or corrected.

## Acceptance criteria

- Root `AGENTS.md` contains the canonical guidance chain and `.agent/**/*.md` discovery patterns.
- Area specialization `AGENTS.md` files do not repeat `## Guidance chain` or `## Discovery patterns`.
- `areas/template/AGENTS.tmpl.md` does not reintroduce the duplicated sections for future specs.
- `MEMORY.md` includes a concise `mempalace_store` example with wing, optional confirmed room, text, and tags.

## Operational constraints

- Token-budget reporting uses a dependency-free estimate of `ceil(chars / 4)` unless a tokenizer dependency is intentionally added later.
- Validation continues to run through Makefile targets: `make lint` and `make build`.
