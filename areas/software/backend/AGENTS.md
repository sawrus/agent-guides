# Backend — guidance index

## What this area covers

Server-side service development: REST / GraphQL API design, domain modeling, database access patterns, async processing, observability, and security. Load after `software/general/` baseline.

## Guidance chain

1. Project `.agent/` baseline (`AGENTS.md` + `.agent/*`)
2. `.agent/rules/*` — always active
3. `.agent/rules/*` — load all for this spec
4. `.agent/skills/*/SKILL.md` — load only the skill matching the current task
5. `.agent/workflows/*` — load the workflow matching the triggered command

## Inherited from general

- SDLC methodology and role responsibilities
- Git / CI / lint / format and code style baselines
- General development and code review workflows

## Backend-specific overrides

- All endpoints must include authZ check, input validation, and structured error response.
- Database changes require a migration file — no schema drift via ORM sync in production.
- Every new module requires observability: at minimum, structured logs and a latency metric.

## Spec map

```text
.agent/
├── rules/
│   ├── architecture.md       ← layering, module boundaries, dependency direction
│   ├── data_access.md        ← ORM usage, query patterns, N+1 prevention
│   ├── security.md           ← authN/authZ, input validation, secret handling
│   └── testing.md            ← test pyramid targets, mock boundaries, contract tests
├── skills/
│   ├── api-design/SKILL.md           ← REST / GraphQL conventions, versioning, contracts
│   ├── async-processing/SKILL.md     ← queues, workers, retry/DLQ patterns
│   ├── database-modeling/SKILL.md    ← schema design, indexes, migration safety
│   ├── observability/SKILL.md        ← structured logging, metrics, distributed tracing
│   └── troubleshooting/SKILL.md      ← systematic debugging, profiling, root-cause analysis
├── workflows/
│   ├── add-migration.md       ← /add-migration
│   ├── create-endpoint.md     ← /create-endpoint
│   ├── debug-issue.md         ← /debug-issue
│   ├── develop-epic.md        ← /develop-epic
│   ├── develop-feature.md     ← /develop-feature
│   ├── refactor-module.md     ← /refactor-module
│   └── test-feature.md        ← /test-feature
└── prompts/
    └── *.md
```

## Discovery patterns

- `.agent/rules/*.md`
- `.agent/skills/*/SKILL.md`
- `.agent/workflows/*.md`
- `.agent/prompts/*.md`
