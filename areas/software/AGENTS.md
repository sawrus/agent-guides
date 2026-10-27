# Software — area index

Application code: backend services first, plus frontend, data, ML, mobile, QA, and application security.

## Spec selection

| Task type | Spec |
|:---|:---|
| Any coding task, bug, refactoring, or review | `general/` (always install it) |
| API and service development in Python, Go, Java | `backend/` |
| Web UI components | `frontend/` |
| Data pipelines, dbt, warehouses | `data-engineering/` |
| ML training, evaluation, serving | `mlops/` |
| iOS, Android | `mobile/` |
| Test strategy and suites | `qa/` |
| Application security, dependencies, secrets | `security/` |

Infrastructure, pipelines, Kubernetes, observability, and incidents live in `areas/devops/`.

## Load order

1. Spec `AGENTS.md` — installed into the project `AGENTS.md`.
2. Rules — Claude Code loads a rule when a file matches its `paths:`; read a `trigger: manual` rule when the
   task touches its topic.
3. Skills — on demand, when the description matches the task.
4. Workflows — when the request matches `selection.use-when` or the user types the trigger.

## Trigger registry

Triggers are unique across all areas; check `areas/devops/AGENTS.md` before you add one.

| Trigger | Spec | Purpose |
|:---|:---|:---|
| `/develop-feature` | general | Build or change behaviour (the general workflow) |
| `/debug-issue` | general | Find the root cause of a bug and fix it |
| `/refactor-module` | general | Restructure code without behaviour change |
| `/code-review-workflow` | general | Review a merge request or diff |
| `/add-migration` | backend | Add a backward-compatible schema migration |

## Specs in this area

```text
areas/software/
├── general/           # shared rules and the general workflows
├── backend/           # API and service development
├── frontend/          # rules only
├── data-engineering/  # rules only
├── mlops/             # rules only
├── mobile/            # rules only
├── qa/                # rules only
└── security/          # rules and the dependency-audit skill
```
