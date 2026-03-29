# AGENTS — root guidance

## Dynamic loading of guidance

The set of loaded guidance is configurable per project and may change per task. Do not assume only statically listed files are available.

Discover and load custom files from the target project when present:

```text
project_dir/
└── .agent/
    ├── rules/
    ├── skills/
    ├── workflows/
    └── prompts/
```

**Discovery patterns:**

- `project_dir/.agent/rules/*`
- `project_dir/.agent/skills/*`
- `project_dir/.agent/workflows/*`
- `project_dir/.agent/prompts/*`

Prefer relative paths in references inside markdown files.

---

## Area and spec selection

When starting a task, resolve the correct area and spec by matching the task domain:

| Domain | Area |
|:---|:---|
| API / service / backend logic | `areas/software/backend/` |
| UI / components / frontend | `areas/software/frontend/` |
| Full product feature (API + UI) | `areas/software/full-stack/` |
| Data pipelines, dbt, warehouses | `areas/software/data-engineering/` |
| ML training, serving, monitoring | `areas/software/mlops/` |
| iOS / Android / cross-platform | `areas/software/mobile/` |
| Internal platform, K8s, Terraform | `areas/software/platform/` |
| Test strategy, QA tooling | `areas/software/qa/` |
| Threat modeling, secure coding | `areas/software/security/` |
| Kubernetes cluster operations | `areas/devops/kubernetes/` |
| CI/CD pipelines | `areas/devops/ci-cd/` |
| IaC, environment provisioning | `areas/devops/infrastructure/` |
| Observability, dashboards, alerts | `areas/devops/observability/` |
| SLOs, incidents, chaos | `areas/devops/sre/` |
| Networking, ingress, TLS, mesh | `areas/devops/networking/` |
| DevSecOps, supply-chain security | `areas/devops/devsecops/` |
| DB operations, backup, migrations | `areas/devops/database-ops/` |
| Cross-cutting / foundational | `areas/software/general/` |

If the task spans multiple areas, load the primary area's full chain and add only the `rules/*` from secondary areas.

---

## Load order (always respected)

1. This root `AGENTS.md`
2. Area `AGENTS.md` (e.g., `areas/software/backend/AGENTS.md`)
3. Spec `rules/*.md` — load all rules for the selected spec
4. Spec `skills/*/SKILL.md` — load only the skill matching the current task (see "When to load" in each skill)
5. Spec `workflows/*.md` — load the workflow matching the slash command trigger

---

## General Development Practices

Cross-cutting practices that apply to every project regardless of area.

### Git Workflow

- Use feature branches with task IDs in branch names (e.g., `feat/TASK-123-add-auth`).
- Commit messages include context: what changed, why, and any relevant ticket reference.
- No direct commits to main or protected branches — all changes via reviewed PRs.

### Makefile Conventions

- Use Makefile for common development tasks accessible to all contributors.
- Include a `help` target listing available commands with descriptions.
- Standard targets: `install`, `dev`, `test`, `lint`, `fmt`, `clean`, `build`.

### Docker Compose

- Use docker-compose for local multi-service development.
- Configure health checks for all dependent services before marking ready.
- Drive configuration via environment variables; no hardcoded values.

### Linting and Formatting

- Configure language-appropriate linters for every project.
- Enforce standards via pre-commit hooks — CI is a safety net, not the primary check.
- Apply consistent formatting across all files on every commit.

### SDLC Methodology

- Follow phases in order: Requirements → Design → Implementation → Verification → Deployment → Maintenance.
- Document requirements before implementation — "we'll figure it out" is not a requirement.
- Conduct design reviews for any change with architectural, security, or data model impact.

### Code Style

- Write self-documenting code with meaningful names — comments explain why, not what.
- Apply DRY principles; avoid duplication across modules.
- Keep functions focused on a single responsibility; extract when a function does two things.

---

## Repository Exploration (mandatory before implementation)

Before executing any workflow, spawn a subagent to explore the repository.

### Role resolution

- Use the role defined in `execution.initiator` of the current workflow.
- If not defined, use the role assigned to the first workflow step.
- Resolve roles only from the current workflow's `roles` section — do not invent roles.

### Purpose

- Understand current architecture and established conventions.
- Identify key modules, entrypoints, and data flows.
- Detect configuration (env, Docker, Makefile, CI).
- Identify components impacted by the proposed change.
- Validate feasibility before any code is written.

### Subagent responsibilities

- Analyze repository structure and dependencies.
- Locate relevant services, modules, and data flows.
- Identify constraints, risks, and integration points.
- Prepare a context summary for the next workflow step.

### Required output

- High-level system overview.
- List of affected modules and files.
- Detected risks and constraints.

### Constraint

This step is **mandatory** and must complete before "Solution Design & Risk Plan" begins.
