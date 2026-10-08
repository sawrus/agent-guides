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

## Dispatch and failure handling

Invoke `instruction_reviewer` and `memory_curator` independently with the same
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
If report persistence is unavailable, finish accepted delivery with an inline status
and concise findings; explain missing links instead of blocking delivery or retrying.
Recommendations are advisory; apply instruction/docs/memory edits in a separate
requested task. Reports are not durable product docs or memory facts.
