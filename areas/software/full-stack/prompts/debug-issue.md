---
workflow: debug-issue
---

# Prompt: `/debug-issue`

Use when: diagnosing a bug in a FastAPI / SQLAlchemy service — from stack trace or symptom through to root cause, fix, and regression test.

---

## Example 1 — Production error with stack trace

**EN:**
```
/debug-issue

Service: order-service (FastAPI + SQLAlchemy async)
Error: 500 Internal Server Error on POST /api/v1/orders
Affected users: 100% of users who apply a discount code; 0% for regular checkout
First seen: 2024-09-13 14:30 UTC (correlates with v2.4.1 deploy at 14:22 UTC)
Stack trace:
  File "src/services/order_service.py", line 147, in create_order
    total = subtotal - order_data['discount_amount']
  KeyError: 'discount_amount'
Logs (request_id=req_abc123):
  INFO  order.validation_passed user_id=42 discount_code=SUMMER20
  INFO  discount.applied code=SUMMER20 amount=15.00
  ERROR order.creation_failed KeyError: 'discount_amount'
Suspected cause: discount service returns Decimal amount but order_service expects field 'discount_amount';
  PR #204 renamed field from 'discount' to 'discount_amount' in discount-service but order-service not updated
```

**RU:**
```
/debug-issue

Сервис: order-service (FastAPI + SQLAlchemy async)
Ошибка: 500 Internal Server Error на POST /api/v1/orders
Затронутые пользователи: 100% пользователей применяющих код скидки; 0% при обычном оформлении
Первое появление: 2024-09-13 14:30 UTC (совпадает с деплоем v2.4.1 в 14:22 UTC)
Stack trace:
  File "src/services/order_service.py", line 147, in create_order
    total = subtotal - order_data['discount_amount']
  KeyError: 'discount_amount'
Логи (request_id=req_abc123):
  INFO  order.validation_passed user_id=42 discount_code=SUMMER20
  INFO  discount.applied code=SUMMER20 amount=15.00
  ERROR order.creation_failed KeyError: 'discount_amount'
Предполагаемая причина: discount сервис возвращает Decimal сумму но order-service ожидает поле 'discount_amount';
  PR #204 переименовал поле с 'discount' на 'discount_amount' в discount-service но order-service не обновлён
```

---

## Example 2 — Performance regression (no error)

**EN:**
```
/debug-issue

Service: product-service
Symptom: GET /api/v1/products p99 latency went from 85ms to 4 200ms after migration PR #198
No errors in logs — just extreme latency
Migration PR #198 added: products_tags junction table (many-to-many between products and tags)
Observed: slow queries only when tags are present; products without tags still fast (85ms)
DB metrics: PostgreSQL CPU 8% (not saturated); query count per request jumped from 3 to ~47
Diagnosis direction: N+1 query — each product loads its tags in a separate query; need joinedload()
Reproduce: run EXPLAIN ANALYZE on GET /products with tags; count SELECT statements in a single request
```

**RU:**
```
/debug-issue

Сервис: product-service
Симптом: p99 задержка GET /api/v1/products выросла с 85ms до 4 200ms после миграции PR #198
Ошибок в логах нет — только экстремальная задержка
Миграция PR #198 добавила: junction таблицу products_tags (many-to-many между products и tags)
Наблюдение: медленные запросы только когда есть теги; продукты без тегов по-прежнему быстрые (85ms)
Метрики БД: PostgreSQL CPU 8% (не насыщен); количество запросов на запрос выросло с 3 до ~47
Направление диагностики: N+1 запрос — каждый продукт загружает теги отдельным запросом; нужен joinedload()
Воспроизвести: запустить EXPLAIN ANALYZE на GET /products с тегами; подсчитать SELECT операторы в одном запросе
```

---

## Example 3 — Intermittent / Race condition

**EN:**
```
/debug-issue

Service: payment-service
Symptom: ~2% of payments marked as FAILED despite Stripe confirming payment succeeded
Pattern: only happens when user clicks "Pay" twice quickly (double-submit)
Error log: "IntegrityError: duplicate key value violates unique constraint payments_idempotency_key"
The payment actually succeeds on first attempt; second attempt raises IntegrityError which is propagated as 500
Root issue: IntegrityError not caught — should return 200 with existing payment, not 500
Fix direction: catch IntegrityError on idempotency key collision → query existing payment → return it
Test: write test that sends two concurrent requests with same idempotency key; verify both return 200 with same payment_id
```

**RU:**
```
/debug-issue

Сервис: payment-service
Симптом: ~2% платежей помечаются как FAILED несмотря на то что Stripe подтверждает успешную оплату
Паттерн: происходит только когда пользователь быстро дважды нажимает "Оплатить" (двойная отправка)
Лог ошибки: "IntegrityError: duplicate key value violates unique constraint payments_idempotency_key"
Платёж фактически проходит с первой попытки; вторая попытка вызывает IntegrityError которая возвращается как 500
Корневая проблема: IntegrityError не перехватывается — должен возвращать 200 с существующим платежом, не 500
Направление исправления: перехватить IntegrityError при коллизии idempotency key → запросить существующий платёж → вернуть его
Тест: написать тест отправляющий два одновременных запроса с одинаковым idempotency key; убедиться что оба возвращают 200 с одинаковым payment_id
```
