---
workflow: create-endpoint
---

# Prompt: `/create-endpoint`

Use when: adding a single new API endpoint to an existing backend service.

---

## Example 1 — Domain Action Endpoint

**EN:**
```
/create-endpoint "Refund Order"

Method: POST /orders/{order_id}/refund
Auth: Bearer token, scope: orders:write
Request body: { reason: string (max 500 chars), amount?: number (partial refund, optional) }
Business rules:
- Order must be in PAID status, else return 400 with error code ORDER_NOT_REFUNDABLE
- If amount not provided: full refund
- If amount > original: return 400 REFUND_EXCEEDS_ORIGINAL
- On success: create refund_transaction, update order status to REFUNDED (or PARTIALLY_REFUNDED), emit order.refunded event
Response: 200 { refund_id, status, amount, processed_at }
Non-functional: idempotency key support via X-Idempotency-Key header
```

**RU:**
```
/create-endpoint "Возврат средств по заказу"

Метод: POST /orders/{order_id}/refund
Auth: Bearer token, scope: orders:write
Тело запроса: { reason: string (макс 500 символов), amount?: number (частичный возврат, опционально) }
Бизнес-правила:
- Заказ должен быть в статусе PAID, иначе 400 с кодом ORDER_NOT_REFUNDABLE
- Если amount не указан: полный возврат
- Если amount > оригинального: 400 REFUND_EXCEEDS_ORIGINAL
- Успех: создать refund_transaction, обновить статус (REFUNDED или PARTIALLY_REFUNDED), emit order.refunded
Ответ: 200 { refund_id, status, amount, processed_at }
Нефункциональное: поддержка idempotency key через заголовок X-Idempotency-Key
```

---

## Example 2 — Read / Query Endpoint

**EN:**
```
/create-endpoint "List User Activity Feed"

Method: GET /users/{user_id}/feed
Auth: Bearer token; user can only access own feed unless admin scope
Query params: limit (default 20, max 100), cursor (pagination), type? (filter by event type)
Response: { items: ActivityEvent[], next_cursor?: string, total_count: int }
ActivityEvent: { id, type, payload, created_at }
Performance: response time p99 < 200ms; use cursor-based pagination, not offset
Constraints: do not expose other users' PII in feed items
```

**RU:**
```
/create-endpoint "Лента активности пользователя"

Метод: GET /users/{user_id}/feed
Auth: Bearer token; пользователь видит только свою ленту, если нет admin scope
Query params: limit (default 20, max 100), cursor (пагинация), type? (фильтр по типу события)
Ответ: { items: ActivityEvent[], next_cursor?: string, total_count: int }
ActivityEvent: { id, type, payload, created_at }
Производительность: p99 < 200ms; cursor-based пагинация, не offset
Ограничения: не раскрывать PII других пользователей в элементах ленты
```

---

## Example 3 — Quick / Minimal

**EN:**
```
/create-endpoint "Health Check"

Method: GET /health
Auth: none
Response: 200 { status: "ok", version: string, uptime_seconds: int }
Must respond in < 50ms; must not trigger DB queries.
```

**RU:**
```
/create-endpoint "Health Check"

Метод: GET /health
Auth: нет
Ответ: 200 { status: "ok", version: string, uptime_seconds: int }
Ответ < 50ms; запросы к БД не допускаются.
```
