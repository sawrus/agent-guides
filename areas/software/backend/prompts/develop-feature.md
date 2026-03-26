---
workflow: develop-feature
---

# Prompt: `/develop-feature`

Use when: starting end-to-end backend feature delivery from a business request to an accepted, tested increment.

---

## Example 1 — New Business Feature

**EN:**
```
/develop-feature "User Subscription Cancellation"

Feature: allow users to cancel their active subscription immediately or at end of billing period.
Acceptance criteria:
- User can cancel via DELETE /subscriptions/{id}
- Cancellation reason is recorded (enum: too_expensive, not_useful, switching_product, other)
- Immediate cancellation: subscription status set to CANCELLED, refund_eligible flag computed
- End-of-period: status set to CANCEL_PENDING, access retained until period end
- Cancellation event emitted to event bus for billing and analytics consumers
Constraints: backward-compatible with existing billing integrations; no downtime; rollback-safe
```

**RU:**
```
/develop-feature "Отмена подписки пользователем"

Фича: пользователь может отменить активную подписку немедленно или по окончании платёжного периода.
Критерии приёмки:
- Отмена через DELETE /subscriptions/{id}
- Причина отмены записывается (enum: too_expensive, not_useful, switching_product, other)
- Немедленная отмена: статус CANCELLED, вычисляется флаг refund_eligible
- Отмена в конце периода: статус CANCEL_PENDING, доступ сохраняется до конца периода
- Событие cancellation публикуется в event bus для billing и analytics
Ограничения: обратная совместимость с текущим billing; без даунтайма; безопасный rollback
```

---

## Example 2 — Technical Feature / Platform Improvement

**EN:**
```
/develop-feature "Rate Limiting on Public API"

Feature: add per-client rate limiting to all public API endpoints.
Acceptance criteria:
- Limit: 100 requests/minute per API key (configurable)
- Response on breach: 429 Too Many Requests with Retry-After header
- Limits tracked in Redis with sliding window algorithm
- Admin endpoint to view current usage per client: GET /admin/rate-limits/{api_key}
- Rate limit headers on every response: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
Constraints: p99 latency increase < 5ms; Redis connection failure must degrade gracefully (fail open with logging)
```

**RU:**
```
/develop-feature "Rate Limiting на публичном API"

Фича: per-client rate limiting для всех публичных эндпоинтов.
Критерии приёмки:
- Лимит: 100 запросов/минуту на API-ключ (конфигурируемо)
- При превышении: 429 Too Many Requests с заголовком Retry-After
- Лимиты хранятся в Redis, алгоритм sliding window
- Эндпоинт для просмотра использования: GET /admin/rate-limits/{api_key}
- Заголовки в каждом ответе: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
Ограничения: рост p99 latency < 5ms; сбой Redis — fail open с логированием
```

---

## Example 3 — Quick / Minimal

**EN:**
```
/develop-feature "Add soft delete to orders"

Feature: orders should not be hard-deleted; add deleted_at timestamp column and filter deleted orders from all default queries.
Constraints: existing queries must not return deleted orders without explicit flag.
```

**RU:**
```
/develop-feature "Soft delete для заказов"

Фича: заказы не удаляются физически; добавить колонку deleted_at и фильтровать удалённые из всех стандартных запросов.
Ограничения: существующие запросы не должны возвращать удалённые заказы без явного флага.
```
