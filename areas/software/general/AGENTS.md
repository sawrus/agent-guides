# Software — general guidance index

This area contains the shared SDLC baseline inherited by all software specialization areas. Load this before any domain-specific guidance.

## What this area covers

Cross-cutting engineering practices that apply regardless of stack: Git workflow, CI/CD standards, linting, code style, SDLC methodology, role responsibilities, and project setup conventions. Every software specialization area inherits from here and adds only domain-specific overrides.

## Inheritance contract

All specialization areas follow this load order:

```
AGENTS.md (scope) → rules (constraints) → skills (execution patterns) → workflows (orchestration)
```

Specializations reference general guidance and keep only domain-specific overrides. Do not duplicate general rules in domain-level files.

## Spec selection

| Task type | Area to load |
|:---|:---|
| API / service development | `software/backend/` |
| UI / component development | `software/frontend/` |
| Full product feature (API + UI) | `software/full-stack/` |
| Data pipelines, dbt, warehouses | `software/data-engineering/` |
| ML training, evaluation, deployment | `software/mlops/` |
| iOS / Android / React Native | `software/mobile/` |
| Infrastructure, K8s, CI/CD, incidents | `software/platform/` |
| Test strategy, coverage, QA tooling | `software/qa/` |
| Security scans, threat modeling | `software/security/` |
| Cross-cutting / unclear domain | `software/general/` |

## Cross-cutting constraints

- **Git discipline** — every change lives in a branch; no direct commits to main.
- **Lint and format** — all files pass configured linters before any handoff.
- **SDLC role separation** — no role consolidation when subagent execution is required.
- **README sync** — public-facing READMEs updated whenever behavior or setup changes.

## Guidance tree

```text
.agent/
├── rules/
│   ├── git-workflow-guide.md          ← branching, commit messages, PR conventions
│   ├── github-workflow-guide.md       ← GitHub-specific CI triggers and branch protection
│   ├── gitlab-ci-guide.md             ← GitLab CI pipeline conventions
│   ├── makefile-guide.md              ← standard Makefile targets and conventions
│   ├── docker-compose-guide.md        ← local multi-service development setup
│   ├── lint-format-guide.md           ← linter config and pre-commit hooks
│   ├── sdlc-methodology-guide.md      ← phase definitions, entry/exit criteria
│   ├── sdlc-role-responsibilities.md  ← role matrix, handoff contracts, DoD
│   ├── readme-sync-guide.md           ← what READMEs must contain and when to update
│   └── code-style-guide.md            ← naming, structure, DRY, single responsibility
├── skills/
│   └── general-dev-tools/SKILL.md     ← cross-stack dev tooling patterns
└── workflows/
    ├── project-setup-workflow.md       ← /project-setup-workflow
    ├── code-review-workflow.md         ← /code-review-workflow
    └── development-cycle-workflow.md   ← /development-cycle-workflow
```
