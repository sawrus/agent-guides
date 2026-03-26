---
workflow: feature-implementation-flow
---

# Prompt: `/feature-implementation-flow`

Use when: implementing a single feature in an existing FastAPI/SQLAlchemy service — following the layered architecture (model → repo → service → endpoint).

---

## Example 1 — State transition with business rules

**EN:**
```
/feature-implementation-flow

Feature: "Refund order"
Existing codebase: src/ (FastAPI + SQLAlchemy async, layered architecture)
Endpoint: POST /api/v1/orders/{order_id}/refund
Request body: { reason: str, amount: Decimal (optional, defaults to full order total) }
Business rules:
  - Only orders with status PAID can be refunded
  - Partial refund: amount must be > 0 and ≤ order total
  - Full refund if amount not provided
  - On refund: create RefundRecord, update order status → REFUNDED, emit OrderRefunded event
  - Idempotency: same order_id + reason within 1 hour = return existing refund (no duplicate)
Error responses:
  - 404 if order not found
  - 403 if order belongs to different user
  - 400 if order not in PAID status (code: ORDER_NOT_REFUNDABLE)
  - 400 if amount > total (code: REFUND_EXCEEDS_TOTAL)
Tests required: service unit tests (all business rules) + API integration tests (all error codes)
```

**RU:**
```
/feature-implementation-flow

Фича: "Возврат заказа"
Существующий код: src/ (FastAPI + SQLAlchemy async, layered architecture)
Эндпоинт: POST /api/v1/orders/{order_id}/refund
Тело запроса: { reason: str, amount: Decimal (необязательно, по умолчанию полная сумма заказа) }
Бизнес правила:
  - Возврат возможен только для заказов со статусом PAID
  - Частичный возврат: amount должен быть > 0 и ≤ итогу заказа
  - Полный возврат если amount не указан
  - При возврате: создать RefundRecord, обновить статус заказа → REFUNDED, отправить событие OrderRefunded
  - Идемпотентность: одинаковые order_id + reason в течение 1 часа = вернуть существующий возврат (без дублирования)
Ответы ошибок:
  - 404 если заказ не найден
  - 403 если заказ принадлежит другому пользователю
  - 400 если заказ не в статусе PAID (code: ORDER_NOT_REFUNDABLE)
  - 400 если amount > total (code: REFUND_EXCEEDS_TOTAL)
Обязательные тесты: unit тесты сервиса (все бизнес правила) + API интеграционные тесты (все коды ошибок)
```

---

## Example 2 — New resource with relationships

**EN:**
```
/feature-implementation-flow

Feature: "Product reviews"
Existing codebase: src/ (order-service extended with product catalog)
Endpoints:
  POST /api/v1/products/{product_id}/reviews   → create review (auth required)
  GET  /api/v1/products/{product_id}/reviews   → paginated list, newest first (no auth)
  DELETE /api/v1/reviews/{review_id}           → delete own review (auth required)
Business rules:
  - One review per user per product (409 if already reviewed)
  - Rating: integer 1–5 (validated)
  - Text: 10–1000 characters
  - User cannot review their own product
  - Product average_rating and review_count cached on Product model (updated on create/delete)
DB changes: create reviews table; add average_rating + review_count columns to products
Performance: GET list uses cursor pagination; N+1 safeguard (eager-load author username)
```

**RU:**
```
/feature-implementation-flow

Фича: "Отзывы на продукты"
Существующий код: src/ (order-service расширенный каталогом продуктов)
Эндпоинты:
  POST /api/v1/products/{product_id}/reviews   → создать отзыв (требуется auth)
  GET  /api/v1/products/{product_id}/reviews   → пагинированный список, сначала новые (без auth)
  DELETE /api/v1/reviews/{review_id}           → удалить свой отзыв (требуется auth)
Бизнес правила:
  - Один отзыв от пользователя на продукт (409 если уже оставлен отзыв)
  - Оценка: целое число 1–5 (валидируется)
  - Текст: 10–1000 символов
  - Пользователь не может оставить отзыв на свой продукт
  - average_rating и review_count продукта кэшируются в модели Product (обновляются при создании/удалении)
Изменения БД: создать таблицу reviews; добавить столбцы average_rating + review_count в products
Производительность: GET список использует cursor пагинацию; защита от N+1 (eager-load имя автора)
```

---

## Example 3 — Background / async job feature

**EN:**
```
/feature-implementation-flow

Feature: "Send order confirmation email (async)"
Trigger: OrderPaid event consumed from RabbitMQ queue
Implementation: ARQ worker task, not a FastAPI endpoint
Task: send_order_confirmation_email(order_id: int)
  - Load order + user email from DB
  - Render email template (templates/order_confirmation.html)
  - Send via SendGrid API (SENDGRID_API_KEY from env)
  - Mark order.confirmation_sent = True
Retry: 3 attempts, exponential backoff (30s, 90s, 270s)
Dead-letter: after 3 failures → log error with order_id + push to failed_notifications queue
Tests: mock SendGrid client; test retry logic; test dead-letter on repeated failure
```

**RU:**
```
/feature-implementation-flow

Фича: "Отправка email подтверждения заказа (async)"
Триггер: событие OrderPaid потребляемое из очереди RabbitMQ
Реализация: ARQ worker задача, не FastAPI эндпоинт
Задача: send_order_confirmation_email(order_id: int)
  - Загрузить заказ + email пользователя из БД
  - Отрисовать email шаблон (templates/order_confirmation.html)
  - Отправить через SendGrid API (SENDGRID_API_KEY из env)
  - Отметить order.confirmation_sent = True
Повторные попытки: 3 попытки, exponential backoff (30s, 90s, 270s)
Dead-letter: после 3 неудач → логировать ошибку с order_id + поместить в очередь failed_notifications
Тесты: mock SendGrid клиент; тест логики повторных попыток; тест dead-letter при повторных сбоях
```
