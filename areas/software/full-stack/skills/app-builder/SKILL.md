---
name: app-builder
type: skill
description: Orchestrate full-stack application scaffolding — determine project type, select tech stack, coordinate agents, scaffold structure.
inputs:
  - implementation_plan.md
outputs:
  - source_code
related-rules:
  - code-quality-guide.md
  - backend-architecture-rule.md
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Agent
---

# App Builder Skill

> Analyzes requests, selects tech stack, scaffolds structure, coordinates agents.

## Project Type Detection

| Keywords | Project Type | Default Stack |
|---|---|---|
| dashboard, admin, crud, internal tool | Full-stack web | Next.js + Prisma + Postgres |
| SaaS, subscription, billing | SaaS web | Next.js + Stripe + Clerk + Prisma |
| API, microservice, backend | REST API | FastAPI (Python) or Express (Node) |
| mobile app, iOS, Android | Mobile | React Native + Expo |
| CLI, command line, terminal | CLI tool | Node.js + Commander or Python + Typer |
| monorepo, multiple apps | Monorepo | Turborepo + pnpm |

## Default 2025 Stack

```
Frontend:  Next.js 15 (App Router) + TypeScript strict + Tailwind + shadcn/ui
Backend:   Next.js Server Actions (collocated) or FastAPI (standalone API)
Database:  PostgreSQL via Prisma (JS) or SQLAlchemy async (Python)
Auth:      Clerk (SaaS/Web) or custom JWT (API-only)
Testing:   Vitest + Playwright (JS) | pytest + Playwright (Python)
Deploy:    Vercel (Next.js) | Railway/Render (FastAPI)
```

## Next.js Full-Stack Directory Structure

```
src/
├── app/                    # Routes only — thin layer
│   ├── layout.tsx
│   ├── (auth)/             # Route group — auth pages
│   ├── (dashboard)/        # Route group — protected pages
│   └── api/[resource]/route.ts
│
├── features/               # Feature-based modules (primary work happens here)
│   ├── orders/
│   │   ├── components/     # UI — OrderCard, OrderList
│   │   ├── actions.ts      # Server Actions — createOrder, cancelOrder
│   │   ├── queries.ts      # Data fetching — getOrder, listOrders
│   │   └── types.ts
│   └── auth/
│       ├── components/
│       ├── actions.ts
│       └── queries.ts
│
├── shared/
│   ├── components/ui/      # Reusable: Button, Input, Card
│   └── lib/                # Utilities, formatters, constants
│
└── server/                 # Server-only (never imported in client components)
    ├── db/                 # Prisma client
    ├── auth/               # Auth config
    └── services/           # External API integrations
```

## Python FastAPI Structure

```
src/
├── api/
│   ├── v1/
│   │   ├── endpoints/      # Thin: validation, call service, return response
│   │   │   ├── orders.py
│   │   │   └── users.py
│   │   └── router.py
│   └── deps.py             # FastAPI dependencies (get_db, get_current_user)
│
├── services/               # Business logic — no DB imports
│   ├── order_service.py
│   └── user_service.py
│
├── repositories/           # DB access only — no business logic
│   ├── order_repo.py
│   └── user_repo.py
│
├── models/                 # SQLAlchemy ORM models
├── schemas/                # Pydantic I/O models
└── core/
    ├── config.py           # Pydantic BaseSettings
    ├── database.py         # Async engine + session factory
    └── security.py         # JWT, password hashing
```

## Agent Coordination Pipeline

```
@analyst          → decompose request into tasks + dependency graph, define API contracts
@developer        → implement backend (API, DB models, services, repositories) and frontend (pages, components, server actions)
@qa               → write unit tests + E2E tests
@team-lead        → review, check architecture compliance, approve
```

Sequential for new projects. Parallel only when tasks are genuinely independent (frontend + backend with agreed contract).

## Scaffolding Process

```
1. Detect project type from request keywords
2. Select tech stack (use defaults; note deviations with justification)
3. Create implementation_plan.md with:
   - Tech stack chosen
   - Directory structure
   - Task list with dependency order
   - Agent assignments per task
4. Present plan to user → wait for approval
5. Execute: @developer backend first (establish contracts) → @developer frontend → @qa
6. @team-lead final review: architecture compliance, test coverage, README complete
```

## Core Files Every Project Must Have

```
README.md          # Setup, env vars, make targets
.env.example       # All required vars with safe placeholder values
Makefile           # install, dev, test, lint, fmt targets
.gitignore         # Language-appropriate ignores
.pre-commit-config.yaml  # Hooks: format, lint, unit tests
```
