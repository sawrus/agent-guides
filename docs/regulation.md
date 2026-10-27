---
covers:
  - areas/software/general/rules/docs-layout.md
  - scripts/check_docs_coverage.py
  - REVIEW_PIPELINE.md
---

# Review regulation: Definition of Done for code review and design review

Status: draft for agreement (v1). Audience: engineers, coding agents, and independent AI auditors (an AI code
reviewer that reads a merge request, and an AI design reviewer that reads `docs/`). The regulation is
vendor-neutral: it does not depend on a host (Claude Code, Codex, OpenCode), a forge (GitHub, GitLab), or a
language.

Terms:

- **Change** — one merge request (pull request) with its commits.
- **Requirement** — a statement of required behaviour from a ticket, a design page, or the request text.
- **Finding** — one problem that a reviewer reports, with severity, evidence, and a suggested fix.
- **Gate** — an automatic check that must pass before merge (CI job, local hook).

Severity scale (shared by both reviews):

| Severity | Meaning | Effect |
|---|---|---|
| `blocker` | Data loss, security hole, broken build, broken contract with a consumer, or a missing requirement. | Merge is not allowed. |
| `major` | Wrong behaviour in a realistic case, missing test for changed behaviour, missing docs coverage. | Merge is not allowed. |
| `minor` | A defect with low impact or an unclear name that can mislead a reader. | Merge allowed; fix or ticket. |
| `info` | A note. | No action required. |

A finding is valid only with evidence: a file and line, a command output, or a quoted requirement. Style that a
linter or formatter enforces is not a finding.

## 1. Definition of Done for code review

A change passes code review when every item below is true. An auditor reports each item as `met`, `partial`,
`missing`, or `not_applicable`, with evidence.

| Id | Item | Evidence |
|---|---|---|
| CR-1 | **Requirements.** Each requirement of the change is `met`. A requirement that is `partial` or `missing` is a `blocker`. Requirements come from the linked ticket, the design page (section 2), or the change description. If there are none, the change description states the expected behaviour. | Requirement list with status per item. |
| CR-2 | **Scope.** The diff changes only what the requirements need. Unrelated edits are split out or explained. | Diff paths vs requirements. |
| CR-3 | **Tests.** Every changed behaviour has a test that fails without the change. A bug fix has a regression test. Deleted tests are explained. | Test names and paths; a run that shows them pass. |
| CR-4 | **Gates green.** The project checks pass on the final commit: build, tests, lint, type check, security scan, as defined by the project (`make test`, `make lint`, or the CI pipeline). | CI pipeline link or command output. |
| CR-5 | **No open blocker or major findings,** including findings from earlier review rounds that are not resolved. | Finding list with status. |
| CR-6 | **Contracts.** Public API, message schemas, database schema, config keys, and CLI flags stay backward compatible, or the change is marked breaking, versioned, and has a migration note for consumers. | Contract diff; version bump; upgrade note. |
| CR-7 | **Data changes.** A schema change has a migration that runs forward and has a rollback or a documented reason why rollback is not possible. Long or locking migrations are called out. | Migration file; rollback step. |
| CR-8 | **Security.** No secrets in the diff. Input from outside the trust boundary is validated. New dependencies are pinned and come from trusted sources. Permissions are least privilege. | Secret scan output; dependency diff. |
| CR-9 | **Operability.** New failure modes are logged with context and, where the project has metrics, counted. Timeouts and retries are explicit for remote calls. | Code references. |
| CR-10 | **Docs coverage.** Code paths changed by the diff are covered by a docs page that changed in the same change (section 3), or the change carries `Docs-Not-Needed: <reason>` and the reason is valid (tests, CI, refactoring without behaviour change). | Coverage check output. |
| CR-11 | **Release notes.** A user-visible change has a CHANGELOG entry and follows the project release policy (version bump if the project requires it). | CHANGELOG diff. |
| CR-12 | **Commits.** Commit messages say why and name the ticket when the project has tickets. No build artifacts or generated files that the project does not track. | `git log`; diff paths. |

**Verdict.** `changes_requested` if any item is `missing`, or if any `blocker`/`major` finding is open.
`approve_with_comments` if only `minor`/`info` findings remain. Otherwise `approve`. The auditor never merges;
an engineer decides.

## 2. Definition of Done for design review

Design review happens before or together with the code change. It reviews the docs pages that describe what
the change must do. An AI design reviewer checks the items below for every docs page that the change adds or
edits, and for every feature or incident directory that the change touches.

### 2.1 Feature page (`docs/<feature>/README.md`)

| Id | Item | Evidence |
|---|---|---|
| DR-1 | **Goal.** One paragraph: the problem, who has it, and the intended outcome. | Quoted paragraph. |
| DR-2 | **Acceptance criteria.** A numbered list of checkable statements. Each criterion can map to a test or a manual check. | List; mapping to tests in the code change. |
| DR-3 | **Out of scope.** What the change does not do. | List. |
| DR-4 | **Contracts.** API endpoints, message schemas, database tables, config keys, CLI flags that the feature adds or changes, with examples. Breaking changes are marked. | Section with examples. |
| DR-5 | **Design.** The chosen approach and the main alternative that was rejected, with the reason. A diagram only when it shows a flow that text cannot. | Section. |
| DR-6 | **Risks and rollout.** Failure modes, data migration, feature flag or staged rollout, and the rollback plan. | Section. |
| DR-7 | **Operability.** Logs, metrics, alerts, and dashboards that the feature needs, or "none" with a reason. | Section. |
| DR-8 | **Coverage.** Frontmatter `covers:` lists the code globs that implement the feature. | Frontmatter. |
| DR-9 | **Consistency.** The page does not contradict the root design pages, other feature pages, or the code on the target branch. | References. |
| DR-10 | **Status.** The page says whether it is `draft`, `agreed`, `implemented`, or `superseded` (with a link). | Status line. |

### 2.2 Incident page (`docs/incidents/<YYYY-MM-DD>-<id>.md`)

| Id | Item | Evidence |
|---|---|---|
| IR-1 | **Impact.** What failed, for whom, from when to when. | Section. |
| IR-2 | **Root cause.** The defect and why it was possible, backed by evidence (logs, queries, commits). Not "human error". | Section with evidence. |
| IR-3 | **Fix.** The change that fixes it, with a link to the change and its regression test. | Link. |
| IR-4 | **Prevention.** At least one action that stops the same class of failure (test, alert, rule, limit), with an owner. | List. |
| IR-5 | **Coverage.** `covers:` lists the code that the fix touched. | Frontmatter. |

### 2.3 Root design page (`docs/<artifact>.md`)

| Id | Item | Evidence |
|---|---|---|
| RD-1 | Describes one whole artifact (service, tool, module, pipeline): purpose, structure, contracts, and how to run and check it. | Sections. |
| RD-2 | Is current: a code change that alters described behaviour updates this page in the same change. | Coverage check. |
| RD-3 | `covers:` lists the code globs of the artifact. | Frontmatter. |

**Verdict.** Same rule as section 1: any `missing` item or open `blocker`/`major` finding → `changes_requested`.
A missing acceptance criteria list (DR-2) is always a `blocker` for a feature page.

## 3. Docs layout and coverage

Every project that adopts this regulation keeps documentation in `docs/` with this layout:

```text
docs/
├── <artifact>.md            # root design page per whole artifact (service, tool, pipeline)
├── <feature-slug>/          # one directory per feature or epic
│   ├── README.md            # feature page (section 2.1)
│   └── ...                  # supporting files: samples, diagrams, measurements
└── incidents/
    └── <YYYY-MM-DD>-<id>.md # incident page (section 2.2)
```

Rules:

| Id | Rule |
|---|---|
| DOC-1 | The docs root holds only root design pages and project-wide policies (release policy, this regulation). Feature work goes into a feature directory. |
| DOC-2 | A feature directory name is a kebab-case slug, optionally prefixed with the ticket id (`ABC-123-payment-split`). |
| DOC-3 | Every root design page, feature page, and incident page has frontmatter `covers:` with code globs relative to the repository root. |
| DOC-4 | **Coverage rule.** If a change modifies a code path, the same change modifies at least one docs page whose `covers:` matches that path. Code paths are all tracked files except `docs/`, tests, CI config, and files the project lists as excluded. |
| DOC-5 | **Exemption.** A change that does not alter behaviour (tests only, CI only, refactoring with unchanged behaviour, dependency bump without API change) adds the commit trailer `Docs-Not-Needed: <reason>`. A reviewer checks that the reason is true (CR-10). |
| DOC-6 | Code that no `covers:` glob matches is reported as uncovered. A project fixes uncovered code by adding a root design page, not by widening a glob to `**`. |
| DOC-7 | Docs describe behaviour and decisions. They do not copy code. |

Enforcement:

- In agent-guides itself: CI fails a pull request that breaks DOC-4 (`make check-docs-coverage`, planned).
- In target projects: the agentic quality gate reports DOC-4 violations as a warning. A project turns the warning
  into a block with `"docs_coverage": "block"` in `.agent/gate.json` (planned).

## 4. How auditors use this document

- Cite item ids (`CR-3`, `DR-2`, `DOC-4`) in every finding and in the summary table.
- Report `not measured` or `unclear` instead of guessing when evidence is not available.
- Keep the report short: a status table, then findings ordered by severity, then a verdict.
- Do not publish or merge; an engineer reviews the report and decides.
