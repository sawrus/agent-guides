---
workflow: project-setup-workflow
---

# Prompt: `/project-setup-workflow`

Use when: bootstrapping a new project from scratch with proper tooling, CI, and conventions.

---

## Example 1 — Python API service

**EN:**
```
/project-setup-workflow "Notifications Service"

Language/framework: Python 3.12 + FastAPI
Database: PostgreSQL (via SQLAlchemy async)
Message queue: Redis (for background job queue)
Team: 3 developers, mono-repo style, GitHub
CI: GitHub Actions
Conventions: conventional commits, squash merge, main branch protected
First milestone: REST API for creating and delivering email/push notifications
```

**RU:**
```
/project-setup-workflow "Сервис уведомлений"

Язык/фреймворк: Python 3.12 + FastAPI
База данных: PostgreSQL (через SQLAlchemy async)
Очередь сообщений: Redis (для очереди фоновых задач)
Команда: 3 разработчика, mono-repo стиль, GitHub
CI: GitHub Actions
Соглашения: conventional commits, squash merge, защита ветки main
Первый milestone: REST API для создания и доставки email/push уведомлений
```

---

## Example 2 — TypeScript monorepo

**EN:**
```
/project-setup-workflow "E-commerce Monorepo"

Language: TypeScript (strict mode)
Structure: Turborepo monorepo — apps/web (Next.js), apps/api (Fastify), packages/shared-types
Database: PostgreSQL + Prisma
CI: GitHub Actions with parallel jobs per workspace
Code quality: ESLint + Prettier + Husky pre-commit hooks
Testing: Vitest for unit, Playwright for E2E
Branch strategy: feature branches → main, no develop branch
```

**RU:**
```
/project-setup-workflow "E-commerce Monorepo"

Язык: TypeScript (strict mode)
Структура: Turborepo monorepo — apps/web (Next.js), apps/api (Fastify), packages/shared-types
База данных: PostgreSQL + Prisma
CI: GitHub Actions с параллельными jobs для каждого workspace
Качество кода: ESLint + Prettier + Husky pre-commit hooks
Тестирование: Vitest для unit, Playwright для E2E
Стратегия веток: feature branches → main, без develop ветки
```

---

## Example 3 — Minimal / Quick start

**EN:**
```
/project-setup-workflow "Internal Admin Tool"

Stack: Python + Flask (simple, no async needed)
No Docker required — runs locally with sqlite for now
CI: GitLab CI, basic lint + test pipeline
Pre-commit: trailing whitespace, end-of-file, ruff
Just needs: Makefile, README, .gitignore, basic CI
```

**RU:**
```
/project-setup-workflow "Внутренний административный инструмент"

Стек: Python + Flask (простой, async не нужен)
Docker не требуется — локально с sqlite на данный момент
CI: GitLab CI, базовый pipeline lint + test
Pre-commit: trailing whitespace, end-of-file, ruff
Нужно только: Makefile, README, .gitignore, базовый CI
```
