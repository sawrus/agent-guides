# Workflow contract hardening: unique triggers, bounded loops, explicit handoffs

## User-facing behavior

Every workflow trigger is now unique across all areas and registered in a trigger registry inside the new
area-level indices `areas/devops/AGENTS.md` and `areas/software/AGENTS.md`. Three commands were renamed:

| Old command | New command | Owner |
|:---|:---|:---|
| `/develop-feature` (full-stack copy) | `/develop-feature-fullstack` | `areas/software/full-stack/` |
| `/debug-issue` (full-stack copy) | `/debug-issue-fullstack` | `areas/software/full-stack/` |
| `/incident-response` (platform copy) | `/service-incident` | `areas/software/platform/` |

`areas/software/backend/` keeps `/develop-feature` and `/debug-issue`; `areas/devops/sre/` keeps
`/incident-response`.

The workflow template contract (`areas/template/workflow.tmpl.md`) is extended:

- `devops-engineer` is the seventh standard role; the initiator must appear in the workflow's own `roles` list.
- Every loop or retry states a maximum iteration count (default 3) and an escalation path.
- Cross-workflow trigger chains are acyclic or carry a circuit breaker (at most one automatic re-trigger).
- Role changes between steps name the handed-over artifact in `Input:`.
- Delivery workflows end with a Document & Version step (docs + `CHANGELOG.md` + version source); incident
  workflows end with `docs/incidents/<date>-<slug>-root-cause.md`.
- Every workflow Exit ends with `**Next:** /trigger` or `**Next:** terminal`.

## Acceptance criteria

- No duplicate `trigger:` values across `areas/*/*/workflows/*.md`.
- Every workflow frontmatter initiator is present in its own `roles:` list; no undeclared or unused step roles;
  no parenthetical role annotations.
- No "loop until"/"repeat until" language without a stated bound and escalation.
- The backup-verify ↔ db-incident, crash-triage ↔ store-submission, smoke-test ↔ deploy-production, and mlops
  incident→retrain→redeploy cycles each contain an explicit circuit-breaker clause.
- `/secret-rotation` contains a rollback failure path; the previous credential version is retained until the new
  one is verified.
- Every workflow Exit contains a `**Next:**` line.

## Operational constraints

- Validation runs through Makefile targets only: `make lint`, `make build`, `make sync-diagrams`,
  `make assess-areas`, `make test`.
- Workflow mermaid diagrams are generated; edit step headings and roles, then run `make sync-diagrams`.
- Saved prompts or automation using the old full-stack/platform commands must switch to the renamed triggers.
