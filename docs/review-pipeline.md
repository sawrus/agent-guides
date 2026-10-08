# Post-task Review Pipeline

## User-facing behavior

After successful top-level delivery, the orchestrator automatically requests two
read-only specialist reports: instruction effectiveness and documentation/memory
hygiene. Recommendations help improve future SDLC work; they are not applied
in the delivery task. Reviews do not replace acceptance, QA, or code review.

The first release covers:
- `/development-cycle-workflow`
- `/develop-feature`
- `/develop-epic`
- `/develop-feature-fullstack`
- `/feature-implementation-flow`
- `/backend-project-full-cycle`

Other workflows are unchanged. Claude, Codex, OpenCode, and existing Gemini
profiles share the same report boundaries. This is guidance-driven orchestration,
not an executable runner or a telemetry collection system.

## Runtime contract

[REVIEW_PIPELINE.md](../REVIEW_PIPELINE.md) is the authoritative execution
protocol. Agentic embeds and installs it in the project root, tracks it in the
managed-file manifest, and links it from generated guidance. Load it only when
a workflow's second-level `Post-task review` hook activates, after acceptance
and the docs/changelog/version completion contract, before the final response.
The workflow initiator coordinates the handoff and saves the reports.

Specialists stay outside workflow `roles`. `/develop-feature` still has exactly
six mandatory SDLC agents; these two specialists are additional reviewers.
Use native agent definitions when available, or their installed profiles with
read-only generic delegation. Without delegation, record unavailability.

One top-level task produces one review pair. Nested workflows and increments
forward observations to their parent; fix/retest loops never launch reviews.
Failed/deferred deliveries do not launch the success hook. A specialist failure
or unavailable provider does not block accepted delivery or trigger retries.

## Evidence and ownership

Both specialists receive the same bounded packet built from existing task
evidence: objectives/result, instructions actually used, relevant diff and docs,
QA/sign-off, observed friction, and available tool/MemPalace activity. Missing
evidence is named explicitly. No full transcript, repository scan, or memory
inventory is required.

`instruction_reviewer` links instruction conflicts, repeated reads/searches,
excess calls, and avoidable rework to their instruction source and proposes exact
edits. Code quality and product requirements remain outside its review scope.
Useful security, acceptance, and operational constraints must be preserved.

`memory_curator` checks changed/consulted docs for sufficiency, freshness,
duplication, contradictions, and retrieval. It assigns each durable fact a
canonical home and evaluates observed MemPalace use. Existing docs should not
be copied into memory without a specific retrieval benefit. At most two extra
narrow searches (`limit: 3`, known project wing) may verify concrete findings;
unavailable MCP and missing history are limitations, not evidence of clean memory.
The curator never writes/deletes memory; executor fact-writing under
[MEMORY.md](../MEMORY.md) continues to apply.

## Reports and acceptance criteria

Artifacts remain under `.reviews/<task-id>/`:
- `instruction-review.md`
- `memory-curation.md`
- `summary.md`

Without a safe task ID, use one `YYYY-MM-DD-HHMMSS` timestamp for all reports.
Each specialist report is at most 500 words with at most five prioritized
findings, sources, consequences, and proposals. Omit empty tables and numeric
scores. No findings requires only a brief conclusion and evidence limitations.
Measurements need telemetry provenance; otherwise use `not measured`.

If artifact persistence fails, finish delivery with an inline status and concise
findings, explaining missing links without retries or blocking acceptance.

Summary records `completed`, `unavailable`, or `failed` per specialist, limitations,
and prioritized follow-ups. Failed/unavailable reviews receive short status
placeholders. The final response links all three artifacts. Examples are under
[examples](review-pipeline/examples/summary.example.md).

Acceptance scenarios:
- A standalone accepted feature runs both specialists once after completion.
- An epic runs one pair after final acceptance, not a pair per increment.
- Failed/deferred delivery does not run the success hook.
- One failed/unavailable specialist leaves the other report intact and does not
  invalidate delivery; the summary records the limitation without automatic retry.
- Without MemPalace, docs are still assessed and memory availability is explicit.
- Without telemetry, reports do not invent token counts or savings.
- Duplicate docs/memory generate a canonical-source recommendation, not automatic
  consolidation, deletion, or another memory copy.

## Installation and rollout

New installations receive the protocol and updated profiles/hooks. Embedded and
checkout knowledge bases behave alike; dry-run does not create the protocol.
Repeated installs preserve unchanged files. Existing unmanaged or user-modified
managed guidance is skipped under normal manifest protection; inspect install
reports and reconcile skipped hooks/profiles manually to enable the full behavior.
No database migration, new MCP requirement, or automatic recommendation application
is introduced. Version 1.1.0 includes the change in Cargo/npm and the changelog.

Validate with `make lint`, `make test`, and `make test-coverage`. Regenerate content
through `make sync-diagrams` and `make build-docs`. The content contract check covers
hooks, role ownership, shared profile boundaries, and the on-demand protocol.
