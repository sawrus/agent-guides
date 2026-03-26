---
workflow: testing-ci-pipeline
---

# Prompt: `/testing-ci-pipeline`

Use when: running the full CI validation pipeline — lint, type check, unit tests, integration tests, E2E — or diagnosing a CI failure.

---

## Example 1 — Full pipeline on PR

**EN:**
```
/testing-ci-pipeline

Project type: backend (Python / FastAPI)
Test scope: all
Trigger: PR #187 ready for review
Pipeline stages (in order):
  1. lint:  ruff check src/ tests/ — zero tolerance
  2. types: mypy src/ --strict
  3. unit:  pytest tests/unit/ -x --tb=short (fail fast)
  4. integration: pytest tests/integration/ --cov=src --cov-report=term-missing
  5. e2e:   pytest tests/e2e/ (Docker Compose stack: app + postgres + redis)
Coverage threshold: 80% lines on src/ — fail CI if below
Environment: GitHub Actions (ubuntu-latest); secrets from GitHub Secrets
Artefacts to upload: coverage/html/, test-results/junit.xml
Expected duration: < 8 minutes total
```

**RU:**
```
/testing-ci-pipeline

Тип проекта: backend (Python / FastAPI)
Скоуп тестов: все
Триггер: PR #187 готов к ревью
Этапы pipeline (по порядку):
  1. lint:  ruff check src/ tests/ — нулевая терпимость
  2. types: mypy src/ --strict
  3. unit:  pytest tests/unit/ -x --tb=short (завершение при первом сбое)
  4. integration: pytest tests/integration/ --cov=src --cov-report=term-missing
  5. e2e:   pytest tests/e2e/ (Docker Compose стек: app + postgres + redis)
Порог покрытия: 80% строк в src/ — не прохождение CI если ниже
Окружение: GitHub Actions (ubuntu-latest); секреты из GitHub Secrets
Артефакты для загрузки: coverage/html/, test-results/junit.xml
Ожидаемая длительность: < 8 минут всего
```

---

## Example 2 — CI failure investigation

**EN:**
```
/testing-ci-pipeline

Mode: diagnose failure
Project type: frontend (TypeScript / React)
Failed CI run: https://github.com/myorg/myapp/actions/runs/9876543210
Failure stage: integration tests (unit passed)
Error output (from CI log):
  FAIL src/features/checkout/__tests__/CheckoutStepper.test.tsx
  ● CheckoutStepper › step 3 payment › renders Stripe Elements
    TypeError: Cannot read properties of undefined (reading 'create')
    at Object.<anonymous> (src/features/checkout/CheckoutStepper.tsx:47:22)
Context: Stripe mock was working yesterday; PR only changed styling (no logic changes)
Hypothesis: Stripe mock not restored between tests — shared state pollution
Investigate: check jest.mock() setup in test file; check if other test modified Stripe global
Fix: ensure jest.resetAllMocks() in afterEach or use jest.isolateModules()
```

**RU:**
```
/testing-ci-pipeline

Режим: диагностика сбоя
Тип проекта: frontend (TypeScript / React)
Неудачный CI запуск: https://github.com/myorg/myapp/actions/runs/9876543210
Этап сбоя: integration тесты (unit прошли)
Вывод ошибки (из CI лога):
  FAIL src/features/checkout/__tests__/CheckoutStepper.test.tsx
  ● CheckoutStepper › step 3 payment › renders Stripe Elements
    TypeError: Cannot read properties of undefined (reading 'create')
    at Object.<anonymous> (src/features/checkout/CheckoutStepper.tsx:47:22)
Контекст: Stripe mock работал вчера; PR изменил только стили (без изменений логики)
Гипотеза: Stripe mock не восстанавливается между тестами — загрязнение shared state
Расследовать: проверить настройку jest.mock() в файле теста; проверить изменял ли другой тест Stripe global
Исправление: обеспечить jest.resetAllMocks() в afterEach или использовать jest.isolateModules()
```

---

## Example 3 — Scope: unit only (quick check)

**EN:**
```
/testing-ci-pipeline

Project type: backend
Test scope: unit only (fast feedback during development)
Command: pytest tests/unit/ -x -q --tb=short
Target: verify that new OrderService.refund() method passes all unit tests before pushing
Expected: < 60 seconds; no Docker, no DB, no network calls
Coverage: skip (coverage only on full run)
```

**RU:**
```
/testing-ci-pipeline

Тип проекта: backend
Скоуп тестов: только unit (быстрая обратная связь при разработке)
Команда: pytest tests/unit/ -x -q --tb=short
Цель: убедиться что новый метод OrderService.refund() проходит все unit тесты перед push
Ожидается: < 60 секунд; без Docker, без БД, без сетевых вызовов
Покрытие: пропустить (покрытие только при полном запуске)
```
