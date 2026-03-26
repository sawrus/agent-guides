---
workflow: refactor-module
---

# Prompt: `/refactor-module`

Use when: improving the structure, readability, or maintainability of existing backend code without changing behavior.

---

## Example 1 — Extract Service Layer

**EN:**
```
/refactor-module "Extract business logic from OrderController into OrderService"

Current state: OrderController has 400+ lines mixing HTTP handling, business rules, and DB queries
Target: clean controller (HTTP only) + OrderService (business logic) + OrderRepository (data access)
Baseline behavior: all existing integration tests for /orders/* must still pass
Constraints: no behavior changes; no new features; one PR per logical extraction step
Risk areas: transaction handling is currently in controller — must move to service layer correctly
```

**RU:**
```
/refactor-module "Вынести бизнес-логику из OrderController в OrderService"

Текущее состояние: OrderController — 400+ строк, смешаны HTTP, бизнес-правила и запросы к БД
Цель: чистый контроллер (только HTTP) + OrderService (бизнес-логика) + OrderRepository (доступ к данным)
Базовое поведение: все существующие integration tests для /orders/* должны пройти после рефакторинга
Ограничения: без изменений поведения; без новых фич; один PR на каждый логический шаг
Риск: управление транзакциями сейчас в контроллере — перенести корректно в service layer
```

---

## Example 2 — Eliminate Duplication

**EN:**
```
/refactor-module "Deduplicate pagination logic across 12 repository methods"

Current state: each repository method has its own copy of limit/offset/cursor pagination boilerplate (~30 lines each)
Target: single PaginationHelper utility used by all repository methods
Baseline: all repository unit tests pass; pagination behavior identical before/after
Approach: strangler fig — introduce helper, migrate methods one at a time, delete old code
```

**RU:**
```
/refactor-module "Устранить дублирование логики пагинации в 12 методах репозитория"

Текущее состояние: каждый метод репозитория содержит собственную копию boilerplate пагинации (~30 строк каждая)
Цель: единый PaginationHelper, используемый всеми методами
Базовое поведение: все unit tests репозитория проходят; поведение пагинации идентично до и после
Подход: strangler fig — ввести helper, мигрировать методы по одному, удалить старый код
```

---

## Example 3 — Quick / Minimal

**EN:**
```
/refactor-module "Replace raw SQL strings with ORM queries in UserRepository"

Scope: UserRepository only (5 methods)
Target: replace string-concatenated SQL with SQLAlchemy ORM; improve readability and eliminate injection surface
Behavior: identical query results; existing tests must pass
```

**RU:**
```
/refactor-module "Заменить raw SQL строки на ORM запросы в UserRepository"

Скоуп: только UserRepository (5 методов)
Цель: заменить конкатенацию SQL на SQLAlchemy ORM; улучшить читаемость, убрать injection surface
Поведение: идентичные результаты; существующие тесты должны пройти
```
