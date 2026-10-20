# Post-task Review Protocol

Load this file only when a workflow explicitly requests a post-task review.
This is agent guidance, not an executable runner or a new SDLC quality gate.

## Activation and ownership

- Apply after successful acceptance/sign-off and the workflow's documentation,
  changelog, and version completion contract, before the final user response.
- The workflow's `execution.initiator` coordinates the review. Specialists are
  additional reviewers outside `roles`; they do not replace SDLC owners or QA.
- Run once per completed top-level task. Nested workflows and increments hand
  observations to the parent instead of launching reviews. Do not run inside
  fix/retest loops, for failed/deferred delivery, or recursively on review reports.
- Track completion in the current task context; reuse completed reports when
  final reporting resumes. Do not introduce a persistent runner or task database.

## Evidence handoff

Prepare one bounded packet for both specialists from evidence already collected:
- task ID, workflow, objective, acceptance outcome, and final result;
- paths and relevant excerpts of instructions actually loaded, including root,
  `.agent/**`, native environment guidance, roles, workflow, and `MEMORY.md`;
- relevant diff excerpts/file list, changed or consulted docs, QA and sign-off links;
- observed friction, repeated reads/searches, retries, and available tool telemetry;
- available MemPalace queries/results/writes and durable facts with source links.

Name missing evidence explicitly. Do not attach the full transcript by default,
scan all docs/memory, or collect fresh telemetry just to populate a report.
Use project-root-relative paths in the packet; resolve protocol references from
that root, including when the current guidance lives under `.opencode/`.

## Optional JEV audit evidence

When JEV native hooks are enabled, include only the completed top-level task's
cleansed records from `.agentic/jev/event-*.json` in the evidence packet. Match
session/task IDs; exclude other tasks. Show the actual questions, answers,
workflow decision, requested/observed models, permission outcomes and fallbacks.
Missing native application evidence is `unknown`, not a successful override.
Hook routing selects the cheapest eligible reviewer when comparable catalog
prices exist; otherwise use the configured lightweight model and state that
cheapest is unproven. Preserve read-only permissions and user model pins.

The instruction reviewer assesses whether each decision helped the task, and
whether project docs/instructions need another action. Name concrete followups
with source, target, owner and `done_when`, or explicitly recommend no changes.
Separate process usefulness from measured cost savings. Do not call JEV to
review JEV, launch extra reviews on every Stop event, or recurse on these reports.

## Dispatch and failure handling

Invoke `instruction-reviewer` and `memory-curator` independently with the same
packet; they may run in parallel when the environment supports it. Prefer the
native installed agent definitions. If only generic delegation exists, pass the
corresponding installed profile as a read-only assignment. If neither is available,
record `unavailable`; do not impersonate a completed specialist review.

Specialists only return Markdown. They must not edit files, call memory-write
or delete tools, or apply recommendations. The orchestrator saves reports.
If a specialist fails, record `failed` and the reason, save the other report, and
finish delivery. Do not retry automatically or block an accepted feature.
This restriction does not revoke executor fact-writing rules in `MEMORY.md`.

## Report contract

Each completed specialist report has at most five prioritized findings and 500
words. Omit empty tables and boilerplate. Use a short no-findings conclusion when
appropriate. Include scope/evidence limitations and actionable recommendations.
Every finding identifies its source, observed consequence, and proposed change;
distinguish observations from inferences. Do not fabricate numeric scores.

Show token, time, or savings numbers only with measured telemetry and provenance.
Otherwise write `not measured`. A shorter instruction is not proof of token savings.
Preserve useful acceptance, security, and operational requirements.

## Artifacts and final handoff

The orchestrator writes:
- `.reviews/<task-id>/instruction-review.md`
- `.reviews/<task-id>/memory-curation.md`
- `.reviews/<task-id>/summary.md`

Without a task ID, use one `YYYY-MM-DD-HHMMSS` timestamp for the whole review.
Use the existing safe task slug; if the supplied ID contains path separators or
traversal segments, use the timestamp instead. Reports stay under `.reviews/`.
For unavailable/failed specialists, write a short status placeholder rather than
inventing findings. Summary lists each status (`completed`, `unavailable`, `failed`),
evidence limits, and prioritized follow-up actions without repeating the reports.
The final user response links all three artifacts and notes material limitations.

## Token accounting

Before `Manual acceptance`, `summary.md` and the final response include a token
usage table. Use one row per agent instance and model, including the coordinator,
SDLC agents, repeated launches, `instruction-reviewer`, and `memory-curator`.
Split model changes into separate rows; a role alone does not identify a launch.
Columns: agent/run ID, role, model, input tokens, cached input tokens, output
tokens, total tokens, and source. State the measurement cutoff with provenance.
The still-unfinished final response is outside that cutoff.

Use only existing available native usage. Do not read hidden host data or gather
full transcripts to fill this table. Write `not measured` for unknown values,
never zero. Label the measured total `partial` if any launch is unmeasured.
Token counts alone do not establish monetary cost or savings.

In the normalized table, input includes cached input; output includes reasoning tokens.
Convert native counters only with documented semantics; otherwise write `not measured`.
Show cached input as a subset and never add it again. Do not add reasoning again.
Deduplicate event IDs. For cumulative counters use the latest documented snapshot
per instance/model rather than summing snapshots. Do not mix cumulative and delta
counters without a proven conversion. If a parent counter includes children,
exclude that inclusive counter from totals unless a documented native breakdown
provides disjoint self usage. Mark excluded values `not measured` and explain why.

Show JEV separately: request count, available input/output tokens, source, and
cutoff. Deduplicate by request ID. Attribute a JEV request to an agent only when
an explicit identifier proves the relationship. Missing telemetry does not block
accepted delivery or trigger extra reviews or model calls.

The offline helper [scripts/review_usage.py](scripts/review_usage.py) normalizes
explicit bounded records supplied by the coordinator; it does not collect usage.
It is optional repository tooling, not installed into target projects. Prepare the
table directly from verified usage when that helper is unavailable.
Its input contract and limitations are documented in
[docs/review-pipeline.md](docs/review-pipeline.md#token-accounting).

## Manual acceptance instructions

`summary.md` and the final user response both end with a `Manual acceptance`
section, so the user can accept any task by hand without reading the reports:
- copy-paste commands, run from the project root, in execution order: setup,
  run or reproduce, and checks (prefer existing Makefile targets);
- the expected result of each command: output, exit code, or changed file;
- manual steps for checks without a command, such as a UI flow or a document
  to read, with the expected observation;
- how to roll back or clean up when the commands change local state.

Use only commands that the delivery actually ran or that its docs define; mark
any command that was not run during delivery as `not run`. Do not invent
credentials, hosts, or data. When no manual check is possible, state why.
If report persistence is unavailable, finish accepted delivery with an inline status
and concise findings; explain missing links instead of blocking delivery or retrying.
Recommendations are advisory; apply instruction/docs/memory edits in a separate
requested task. Reports are not durable product docs or memory facts.
