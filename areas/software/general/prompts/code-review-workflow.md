---
workflow: code-review-workflow
---

# Prompt: `/code-review-workflow`

Use when: reviewing an open pull/merge request or a specific code change.

---

## Example 1 — Feature PR review

**EN:**
```
/code-review-workflow PR #87 "Add rate limiting to public API"

PR scope: adds Redis-backed sliding window rate limiter to all /api/v1/* endpoints.
Focus areas:
- Correctness of sliding window algorithm
- Redis failure handling (should degrade gracefully, not block requests)
- Test coverage for rate limit breach (429) and header presence
- No hardcoded config values (limits must be env-configurable)
Files changed: src/middleware/rate_limit.py, tests/test_rate_limit.py, src/config.py
```

**RU:**
```
/code-review-workflow PR #87 "Добавить rate limiting на публичный API"

Скоуп PR: Redis-backed sliding window rate limiter для всех /api/v1/* эндпоинтов.
Фокус:
- Корректность алгоритма sliding window
- Обработка сбоя Redis (должен деградировать gracefully, не блокировать запросы)
- Покрытие тестами для 429 ответа и наличия заголовков
- Нет hardcoded значений (лимиты настраиваются через env)
Изменённые файлы: src/middleware/rate_limit.py, tests/test_rate_limit.py, src/config.py
```

---

## Example 2 — Architecture-focused review

**EN:**
```
/code-review-workflow PR #104 "Migrate order processing to event-driven"

This is a large architectural PR. Key review concerns:
- Does OrderService still have any direct calls to PaymentService? (should emit event only)
- Is the dual-write period (sync + async) clearly temporary and documented?
- Are events idempotent? If consumer replays an event, is it safe?
- Are all new message schemas versioned?
Diff size: ~800 lines across 12 files
```

**RU:**
```
/code-review-workflow PR #104 "Миграция обработки заказов на event-driven"

Это большой архитектурный PR. Ключевые вопросы:
- Нет ли прямых вызовов OrderService → PaymentService? (должен только emit event)
- Чётко ли обозначен dual-write период как временный и задокументирован?
- Идемпотентны ли события? Безопасен ли повторный replay у консьюмера?
- Версионированы ли все новые message schemas?
Размер diff: ~800 строк в 12 файлах
```

---

## Example 3 — Quick / Security-focused

**EN:**
```
/code-review-workflow PR #91 "Add admin user deletion endpoint"

Security-focused review: DELETE /admin/users/{id}
Check: auth middleware applied (admin scope required); audit log written on deletion;
soft-delete or hard-delete with confirmation; no IDOR possible via id parameter.
```

**RU:**
```
/code-review-workflow PR #91 "Добавить эндпоинт удаления пользователей для администратора"

Ревью с фокусом на безопасность: DELETE /admin/users/{id}
Проверить: применён auth middleware (требуется admin scope); запись в audit log при удалении;
soft-delete или hard-delete с подтверждением; нет возможности IDOR через параметр id.
```
