# Software — area guidance index

Load this file before any spec-level guidance in `areas/software/`.

## What this area covers

Application development across the stack: backend services, frontend UIs, full-stack features, data pipelines,
ML systems, mobile apps, platform tooling, QA, and application security. Used by agents implementing product
changes — every spec assumes work flows Requirements → Design → Implementation → Verification and ends with
documentation and versioning.

## Spec selection

Match the task to the spec that owns it:

| Task type | Spec to load |
|:---|:---|
| API / service development | `backend/` |
| UI / component development | `frontend/` |
| Full product feature (API + UI) | `full-stack/` |
| Data pipelines, dbt, warehouses | `data-engineering/` |
| ML training, evaluation, deployment | `mlops/` |
| iOS / Android / React Native | `mobile/` |
| App infrastructure, deploys, service incidents | `platform/` |
| Test strategy, coverage, QA tooling | `qa/` |
| Security scans, threat modeling | `security/` |
| Cross-cutting / unclear domain | `general/` |

If the task spans multiple specs, load the primary spec's full chain, then the secondary spec's `rules/*` only.
`general/` is the shared SDLC baseline inherited by every spec; spec workflows override the general delivery
workflows (`/development-cycle-workflow`, `/code-review-workflow`) for their domain — when a spec workflow exists
for the task, use it instead of the general one.

## Cross-cutting constraints

- **Standard roles** — workflows use only: `product-owner`, `pm`, `team-lead`, `developer`, `qa`, `designer`,
  `devops-engineer`. The initiator appears in the workflow's own `roles` list.
- **Bounded loops** — every fix/retest or review loop states a maximum (default 3 iterations) and an escalation
  path; cross-workflow trigger chains are acyclic or carry a circuit breaker.
- **Completion contract** — delivery workflows end with a Document & Version step: docs under `docs/**`,
  `CHANGELOG.md`, and version bump. Incident workflows end with `docs/incidents/<date>-<slug>-root-cause.md`.
- **Explicit handoffs** — when the acting role changes, the receiving step names the artifact handed over;
  workflow Exits name the follow-up workflow (`Next: /<trigger>`) or state `terminal`.

## Load order

1. This file (`areas/software/AGENTS.md`)
2. `general/AGENTS.md` and `general/rules/*.md` — shared SDLC baseline
3. Spec `AGENTS.md` (`areas/software/<spec>/AGENTS.md`)
4. Spec `rules/*.md` — all rules for the selected spec
5. Spec `skills/*/SKILL.md` — on-demand, matching "When to load"
6. Spec `workflows/*.md` — matching the slash command trigger

## Trigger registry

Every workflow trigger in this area. Triggers are unique across ALL areas — check `areas/devops/AGENTS.md` too
before adding one.

| Trigger | Spec | Purpose |
|:---|:---|:---|
| `/develop-feature` | backend | Deliver a backend feature |
| `/develop-epic` | backend | Deliver a multi-feature epic |
| `/create-endpoint` | backend | Add an API endpoint |
| `/add-migration` | backend | Add a database migration |
| `/refactor-module` | backend | Refactor a module safely |
| `/debug-issue` | backend | Diagnose and fix a backend bug |
| `/test-feature` | backend | Test a delivered feature |
| `/backfill-data` | data-engineering | Backfill historical data |
| `/data-quality-incident` | data-engineering | Handle a data quality incident |
| `/lineage-trace` | data-engineering | Trace data lineage |
| `/new-model` | data-engineering | Build a new dbt model |
| `/schema-migration` | data-engineering | Migrate a warehouse schema |
| `/a11y-fix` | frontend | Fix accessibility issues |
| `/bundle-analyze` | frontend | Analyze bundle size |
| `/release-prep` | frontend | Prepare a frontend release |
| `/scaffold-component` | frontend | Scaffold a UI component |
| `/visual-regression` | frontend | Run visual regression checks |
| `/backend-project-full-cycle` | full-stack | Deliver a backend project end-to-end |
| `/develop-feature-fullstack` | full-stack | Deliver a full-stack feature |
| `/debug-issue-fullstack` | full-stack | Debug a full-stack issue |
| `/feature-implementation-flow` | full-stack | Implement a feature increment |
| `/testing-ci-pipeline` | full-stack | Run the test/CI quality path |
| `/project-setup-workflow` | general | Bootstrap a new project |
| `/code-review-workflow` | general | Review a change set |
| `/development-cycle-workflow` | general | Generic ticket-to-merge cycle |
| `/champion-challenger` | mlops | Compare candidate models |
| `/deploy-endpoint` | mlops | Deploy a model endpoint |
| `/evaluate-model` | mlops | Evaluate a trained model |
| `/model-incident` | mlops | Handle a model incident |
| `/train-experiment` | mlops | Run a training experiment |
| `/crash-triage` | mobile | Triage a mobile crash spike |
| `/device-testing` | mobile | Run device-matrix testing |
| `/ota-update` | mobile | Ship an over-the-air update |
| `/release-build` | mobile | Produce a release build |
| `/store-submission` | mobile | Submit to app stores |
| `/cost-audit` | platform | Audit infrastructure cost |
| `/deploy-production` | platform | Deploy to production |
| `/drift-check` | platform | Check config drift |
| `/service-incident` | platform | Handle an application incident |
| `/provision-env` | platform | Provision an app environment |
| `/flakiness-investigation` | qa | Investigate flaky tests |
| `/performance-audit` | qa | Audit performance |
| `/regression-suite` | qa | Run the regression suite |
| `/smoke-test` | qa | Smoke-test a deployment |
| `/test-coverage-report` | qa | Report test coverage |
| `/compliance-report` | security | Produce a compliance report |
| `/pen-test-sim` | security | Simulate a penetration test |
| `/secret-rotation` | security | Rotate a production secret |
| `/security-scan` | security | Run security scans |
| `/threat-model-review` | security | Review a threat model |

## Specs in this area

```text
areas/software/
├── backend/           # API and service development
├── data-engineering/  # pipelines, dbt, warehouses
├── frontend/          # UI and component development
├── full-stack/        # API + UI product features
├── general/           # shared SDLC baseline
├── mlops/             # ML training, evaluation, serving
├── mobile/            # iOS, Android, React Native
├── platform/          # app deploys, environments, incidents
├── qa/                # test strategy and tooling
└── security/          # scans, threat modeling, secrets
```
