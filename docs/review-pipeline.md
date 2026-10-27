---
covers:
  - REVIEW_PIPELINE.md
  - scripts/lint_review_pipeline.py
  - scripts/review_usage.py
  - extensions/*/agents/instruction-reviewer.*
  - extensions/*/agents/memory-curator.*
---

# Post-task Review Pipeline

## User-facing behavior

After successful top-level delivery, the orchestrator automatically requests two
read-only specialist reports: instruction effectiveness and documentation/memory
hygiene. Recommendations help improve future SDLC work; they are not applied
in the delivery task. Reviews do not replace acceptance, QA, or code review.

Since the content cleanup no pack workflow carries the hook: the ten role-neutral workflows have no
`roles` or `execution.initiator` (docs/artifact-standard.md, ART-W1), so the pipeline runs only for a project or
company workflow that adds a `Post-task review` section with an initiator. `scripts/lint_review_pipeline.py`
checks such hooks when they are registered in its `WORKFLOWS` table; the table is empty for the pack.

Claude, Codex, OpenCode, and existing Gemini
profiles share the same report boundaries. This is guidance-driven orchestration,
not an executable runner or a telemetry collection system.

## Runtime contract

[REVIEW_PIPELINE.md](../REVIEW_PIPELINE.md) is the authoritative execution
protocol. Agentic embeds and installs it in the project root, tracks it in the
managed-file manifest, and links it from generated guidance. Load it only when
a workflow's second-level `Post-task review` hook activates, after acceptance
and the docs/changelog/version completion contract, before the final response.
The workflow initiator coordinates the handoff and saves the reports.

Specialists stay outside workflow `roles`; they are additional reviewers.
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

`instruction-reviewer` links instruction conflicts, repeated reads/searches,
excess calls, and avoidable rework to their instruction source and proposes exact
edits. Code quality and product requirements remain outside its review scope.
Useful security, acceptance, and operational constraints must be preserved.

`memory-curator` checks changed/consulted docs for sufficiency, freshness,
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
placeholders. The final response links all three artifacts.

Since 1.5.0, `summary.md` and the final response end with a `Manual acceptance`
section. It lists copy-paste commands from the project root in execution order
(setup, run, checks; Makefile targets first), the expected result of each command,
manual steps for checks without a command, and rollback or cleanup. Commands that
delivery did not run are marked `not run`; no credentials or hosts are invented.
Examples are under
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

## Token accounting

Since 1.6.0, the summary and final response show usage per agent instance and
model before `Manual acceptance`. Include the coordinator, SDLC agents, repeated
launches and both reviewers. Unknown values are `not measured`; measured totals
are labeled partial when coverage is incomplete. Name the source and cutoff;
the unfinished final response is not yet measured. JEV requests and usage appear
separately. This report applies outside the JEV comparison pilot too.

Use existing native usage only. Cached input is part of input; reasoning is part
of output. Neither is added twice. Deduplicate events, take the latest cumulative
snapshot per instance/model, and exclude child-inclusive parent counters when no
reliable self-only breakdown exists. Do not infer money or savings from tokens.
Lack of usage does not block acceptance or require fresh telemetry collection.

The optional repository helper `scripts/review_usage.py` accepts a JSON array on
stdin and returns JSON on stdout. It reads no files or host internals. It is an
offline normalizer, not a required installed runtime component. Each input record
has this explicit contract:

- `agent_id`, `role`, `model`: launch identity and actual model; do not substitute
  a JEV recommendation for an unknown observed model.
- `event_id`, `source`, `cutoff`: native event identity, provenance and measurement
  boundary. Duplicate equal events count once; conflicting duplicates are unknown.
- `kind`: `delta` for disjoint increments or `cumulative` for snapshots. Cumulative
  records require an increasing integer `sequence`. Mixing kinds is unknown.
- `input_tokens`, `cached_input_tokens`, `output_tokens`, `reasoning_tokens`:
  nonnegative integers or JSON `null` for unknown. Subset counters are not added.
- `scope`: `self` (default) or `includes_children`. Adapters must explicitly mark
  inclusive counts. The helper cannot infer native host counter semantics.
- For JEV only, `channel: "jev"` and `request_id`: separate request accounting.
  Provide records even when request usage is unknown so calls are counted.

The helper emits one row per agent/model, separate JEV rows and request count,
measured totals, and partial flags. Unknown source/cutoff, ambiguous counters and
invalid subset values yield unknown usage. A total needs both input and output;
known input alone does not become a complete total. The helper cannot reconstruct
missing launches: the coordinator must include an unknown record for each known
launch lacking usage. Counter adapters must establish disjoint windows and scope
before calling it. The helper does not estimate missing measurements.

Acceptance includes synthetic cases for full/partial usage, cache subsets,
cumulative snapshots, duplicate events, multiple launches of one role, model
changes, both reviewers, separate JEV requests and inclusive parent counters.

## Installation and rollout

New installations receive the protocol and updated profiles/hooks. Embedded and
checkout knowledge bases behave alike; dry-run does not create the protocol.
Repeated installs preserve unchanged files. Existing unmanaged or user-modified
managed guidance is skipped under normal manifest protection; inspect install
reports and reconcile skipped hooks/profiles manually to enable the full behavior.
No database migration, new MCP requirement, or automatic recommendation application
is introduced. Version 1.1.0 includes the change in Cargo/npm and the changelog.

Validate with `make lint`, `make test`, and `make test-coverage`. Regenerate the docs
catalog through `make build-docs`. The content contract check covers
hooks, role ownership, shared profile boundaries, and the on-demand protocol.
