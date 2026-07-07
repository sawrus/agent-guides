# Full Stack — guidance index

## What this area covers

End-to-end product feature development spanning backend services and frontend interfaces: API design, backend architecture, database access, async processing, frontend integration, testing pipelines, and full project lifecycle management.

## Inherited from general

- SDLC methodology, role responsibilities, and handoff contracts
- Git / CI / lint / format and code style baselines
- General development and code review workflows

## Full-stack-specific constraints

- API contracts are versioned and documented before implementation; no breaking changes without a migration path.
- Frontend and backend changes for the same feature ship together in a coordinated, backward-compatible rollout.
- Every new feature includes end-to-end tests covering at least the critical user path.

## Spec map

```text
.agent/
├── rules/
│   ├── api-design-guide.md            ← REST/GraphQL/tRPC conventions, versioning
│   ├── backend-architecture-rule.md   ← layering, module boundaries, DI
│   ├── database-access-guide.md       ← ORM patterns, query safety, N+1 prevention
│   ├── database-migrations-guide.md   ← migration safety, backward compatibility
│   ├── async-concurrency-guide.md     ← queues, workers, deadlock prevention
│   ├── background-jobs-guide.md       ← job design, retry, DLQ
│   ├── error-handling-guide.md        ← error taxonomy, propagation, user messaging
│   ├── logging-observability-guide.md ← structured logs, trace IDs, metrics
│   ├── security-guide.md              ← authN/authZ, input validation, secret handling
│   ├── testing-ci-guide.md            ← test pyramid, CI checks, coverage thresholds
│   ├── e2e-test-guide.md              ← e2e tool setup, test scope, flakiness policy
│   ├── code-quality-guide.md          ← naming, DRY, single responsibility
│   ├── env-settings-guide.md          ← environment config, secrets, local setup
│   ├── domain-models-guide.md         ← entity design, value objects, aggregates
│   └── project-guide.md               ← folder structure, module boundaries, tech stack
├── skills/
│   ├── api-design-principles/SKILL.md   ← REST best practices, GraphQL schema design
│   ├── api-patterns/SKILL.md            ← auth, rate limiting, versioning, tRPC
│   ├── app-builder/SKILL.md             ← project scaffolding, templates, tech stack detection
│   ├── backend-developer/SKILL.md       ← service patterns, DI, repository design
│   ├── blackbox-test/SKILL.md           ← external API testing, contract validation
│   └── prompt-project-planner/SKILL.md  ← project planning, milestone scoping
├── workflows/
│   ├── develop-feature-fullstack.md    ← /develop-feature-fullstack
│   ├── debug-issue-fullstack.md        ← /debug-issue-fullstack
│   ├── backend-project-full-cycle.md   ← /backend-project-full-cycle
│   ├── feature-implementation-flow.md  ← /feature-implementation-flow
│   └── testing-ci-pipeline.md          ← /testing-ci-pipeline
└── prompts/
    └── *.md
```
