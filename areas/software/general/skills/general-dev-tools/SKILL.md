---
name: general-dev-tools
type: skill
description: Core development tools used across any project — git, docker, make, CI/CD, linting, formatting, pre-commit hooks.
inputs:
  - task_description
  - project_context
outputs:
  - working_environment
  - executed_commands
related-rules:
  - git-workflow-guide.md
  - makefile-guide.md
  - docker-compose-guide.md
  - lint-format-guide.md
  - github-workflow-guide.md
  - gitlab-ci-guide.md
  - readme-sync-guide.md
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# General Dev Tools Skill

> **Expertise:** Git, Docker Compose, Makefile, GitHub Actions, GitLab CI, shell scripting, linting, formatting, pre-commit hooks.

## Rules for the files you change

Read the matching rule in `.agent/rules/` before you edit: `makefile-guide.md` (`Makefile`, `*.mk`),
`docker-compose-guide.md` (compose files), `lint-format-guide.md` (linter, formatter, pre-commit config),
`github-workflow-guide.md` (`.github/**`), `gitlab-ci-guide.md` (GitLab CI), `readme-sync-guide.md` (setup or
usage that `README.md` documents), `git-workflow-guide.md` (branches, commits, pull requests).

## Mindset

- **Repeatability:** All setup is automatable via `make` targets. `make install && make dev` must work on a clean machine.
- **Portability:** Commands work consistently across developer machines and CI.
- **Security:** Never commit secrets. Use env vars; secret managers for production.
- **Fail loudly:** Check exit codes; prefer explicit error messages over silent failures.

---

## Git Patterns

### Branch naming
```bash
feature/<task-id>-short-desc    # e.g. feature/PROJ-42-add-search
fix/<task-id>-short-desc        # e.g. fix/PROJ-55-null-pointer
chore/<description>             # e.g. chore/upgrade-dependencies
release/<version>               # e.g. release/2.4.0
```

### Commit convention (Conventional Commits)
```bash
feat(scope): add user search endpoint      # new feature
fix(auth): handle expired token on refresh # bug fix
chore(deps): upgrade pydantic to 2.x       # maintenance
docs(api): update endpoint reference       # docs only
test(orders): add edge case for zero qty   # tests only
refactor(repo): extract pagination helper  # no behavior change
```

### Common operations
```bash
# Create and track feature branch
git checkout -b feature/PROJ-42-add-search
git push -u origin feature/PROJ-42-add-search

# Rebase on latest main before PR
git fetch origin
git rebase origin/main

# Squash last N commits before merge
git rebase -i HEAD~3

# Undo last commit (keep changes staged)
git reset --soft HEAD~1

# Find which commit introduced a bug
git bisect start
git bisect bad HEAD
git bisect good <known-good-sha>
```

### `.gitignore` essentials
```
# Python
__pycache__/ *.pyc .venv/ .env *.egg-info/ dist/ .pytest_cache/ .mypy_cache/
# Node
node_modules/ dist/ .env .env.local coverage/
# General
.DS_Store *.log .idea/ .vscode/ *.swp
```

---

## Makefile Patterns

### Standard target set (required for all projects)
```makefile
.PHONY: install dev test lint fmt clean help

install:        ## Install all dependencies
	pip install -r requirements.txt -r requirements-dev.txt
	pre-commit install

dev:            ## Start local development environment
	docker compose up -d
	uvicorn src.main:app --reload --port 8000

test:           ## Run test suite
	pytest tests/ -v --cov=src --cov-report=term-missing

lint:           ## Run linter (zero-tolerance)
	ruff check src/ tests/
	mypy src/

fmt:            ## Format code in-place
	ruff format src/ tests/
	ruff check --fix src/ tests/

clean:          ## Remove generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	rm -rf .coverage htmlcov/ dist/ build/

help:           ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
```

### For Node/JS projects
```makefile
install:        ## Install dependencies
	npm ci
	npx husky install

dev:            ## Start dev server
	npm run dev

test:           ## Run tests
	npm test -- --coverage --watchAll=false

lint:           ## Lint
	npx eslint src/ --max-warnings 0

fmt:            ## Format
	npx prettier --write src/
```

---

## Docker Compose Patterns

### Standard multi-service setup
```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - .:/app  # Live reload in dev only

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  pgdata:
```

### `.env.example` (always commit this, never `.env`)
```bash
# Application
APP_ENV=development
SECRET_KEY=change-me-in-production
LOG_LEVEL=DEBUG

# Database
DB_NAME=myapp
DB_USER=myapp
DB_PASSWORD=localpassword
DATABASE_URL=postgresql+asyncpg://myapp:localpassword@localhost:5432/myapp

# Redis
REDIS_URL=redis://localhost:6379/0
```

---

## CI/CD Pipeline Patterns

### GitHub Actions — standard CI
```yaml
# .github/workflows/ci.yml
name: CI
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: testdb
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }

      - name: Install
        run: make install

      - name: Lint
        run: make lint

      - name: Test
        run: make test
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/testdb
```

### GitLab CI — standard pipeline
```yaml
# .gitlab-ci.yml
stages: [lint, test, build]

default:
  image: python:3.12-slim

lint:
  stage: lint
  script: [pip install ruff mypy, make lint]

test:
  stage: test
  services: [postgres:16]
  variables:
    DATABASE_URL: postgresql+asyncpg://test:test@postgres/testdb
    POSTGRES_DB: testdb
    POSTGRES_USER: test
    POSTGRES_PASSWORD: test
  script: [make install, make test]

build:
  stage: build
  script: [docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .]
  only: [main]
```

---

## Pre-commit Configuration

### `.pre-commit-config.yaml` — standard set
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-merge-conflict
      - id: detect-private-key         # Catch accidental secret commits
      - id: check-added-large-files
        args: ['--maxkb=500']

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  # For Node projects, replace above with:
  # - repo: https://github.com/pre-commit/mirrors-prettier
  #   rev: v3.1.0
  #   hooks: [{id: prettier}]
```

```bash
# Install and run
pre-commit install
pre-commit run --all-files   # Run on all files once to baseline
```

---

## Quality Gate Checklist

Before every PR:
```bash
make lint    # Zero errors — never suppress warnings
make fmt     # No diffs after formatting
make test    # All tests pass; coverage ≥ threshold
```

CI must enforce all three. Branch protection requires CI green before merge.
