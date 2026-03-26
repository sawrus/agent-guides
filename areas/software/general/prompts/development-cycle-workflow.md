---
workflow: development-cycle-workflow
---

# Prompt: `/development-cycle-workflow`

Use when: starting any development task from a ticket, issue, or verbal request.

---

## Example 1 — Feature ticket

**EN:**
```
/development-cycle-workflow PROJ-142 "Add pagination to GET /products"

Task: the endpoint currently returns all products with no limit. Add cursor-based pagination.
Acceptance criteria:
- Query params: limit (default 20, max 100), cursor (opaque string)
- Response: { items: Product[], next_cursor?: string }
- Existing clients with no query params get first 20 results (no breaking change)
Constraints: no new dependencies; reuse existing DB query helpers
```

**RU:**
```
/development-cycle-workflow PROJ-142 "Добавить пагинацию в GET /products"

Задача: эндпоинт возвращает все продукты без ограничений. Добавить cursor-based пагинацию.
Критерии приёмки:
- Query params: limit (по умолчанию 20, макс 100), cursor (непрозрачная строка)
- Ответ: { items: Product[], next_cursor?: string }
- Существующие клиенты без параметров получают первые 20 результатов (без breaking change)
Ограничения: без новых зависимостей; переиспользовать существующие DB helpers
```

---

## Example 2 — Bug fix

**EN:**
```
/development-cycle-workflow PROJ-198 "Fix: user session expires immediately after login on Safari"

Bug: users on Safari 17 are logged out immediately after successful login.
Observed: redirect to /login happens 2 seconds after landing on /dashboard
Suspected cause: SameSite=Strict cookie attribute blocks cross-origin redirect
Environment: only Safari 17+; Chrome and Firefox unaffected
Expected: reproduce, fix, add regression test, document root cause
```

**RU:**
```
/development-cycle-workflow PROJ-198 "Фикс: сессия пользователя немедленно истекает после логина в Safari"

Баг: пользователи в Safari 17 выходят из системы сразу после успешного входа.
Наблюдение: редирект на /login происходит через 2 секунды после перехода на /dashboard
Предполагаемая причина: атрибут SameSite=Strict блокирует cross-origin редирект
Среда: только Safari 17+; Chrome и Firefox не затронуты
Ожидание: воспроизвести, исправить, добавить regression test, задокументировать причину
```

---

## Example 3 — Chore / Quick task

**EN:**
```
/development-cycle-workflow PROJ-201 "Upgrade pydantic from 1.x to 2.x"

Scope: migrate all Pydantic models in src/ to v2 syntax.
Key changes: BaseModel.dict() → .model_dump(); validators use @field_validator; orm_mode → from_attributes.
Constraints: no behavior changes; all existing tests must pass after migration.
```

**RU:**
```
/development-cycle-workflow PROJ-201 "Обновить pydantic с 1.x до 2.x"

Скоуп: мигрировать все Pydantic модели в src/ на синтаксис v2.
Ключевые изменения: BaseModel.dict() → .model_dump(); валидаторы через @field_validator; orm_mode → from_attributes.
Ограничения: без изменений поведения; все существующие тесты должны пройти после миграции.
```
