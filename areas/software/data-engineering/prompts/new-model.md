---
workflow: new-model
---

# Prompt: `/new-model`

Use when: scaffolding a new dbt model with sources, staging, mart layers, YAML documentation, and data quality tests.

---

## Example 1 — Domain mart model

**EN:**
```
/new-model "orders_daily_summary"

Layer: mart (business-facing, consumed by BI dashboards)
Source data:
  - stg_orders: order_id, user_id, status, created_at, total_amount, currency
  - stg_order_items: order_id, product_id, quantity, unit_price
  - stg_users: user_id, country, acquisition_channel
Grain: one row per (date, country, acquisition_channel)
Metrics to compute:
  - order_count, gross_revenue_usd, avg_order_value_usd
  - new_users_who_ordered (first order in period)
  - refund_count, refund_amount_usd
Currency: normalise all amounts to USD (use exchange_rates seed table)
Materialisation: table (refreshed daily via Airflow DAG at 03:00 UTC)
Tests required: not_null on date + country, accepted_values for status, referential integrity order_id
Output: models/mart/orders_daily_summary.sql + schema.yml with column descriptions
```

**RU:**
```
/new-model "orders_daily_summary"

Слой: mart (для бизнеса, используется BI дашбордами)
Исходные данные:
  - stg_orders: order_id, user_id, status, created_at, total_amount, currency
  - stg_order_items: order_id, product_id, quantity, unit_price
  - stg_users: user_id, country, acquisition_channel
Гранулярность: одна строка на (дата, страна, канал привлечения)
Вычисляемые метрики:
  - order_count, gross_revenue_usd, avg_order_value_usd
  - new_users_who_ordered (первый заказ за период)
  - refund_count, refund_amount_usd
Валюта: нормализовать все суммы в USD (использовать seed таблицу exchange_rates)
Материализация: table (обновляется ежедневно через Airflow DAG в 03:00 UTC)
Обязательные тесты: not_null на date + country, accepted_values для status, referential integrity order_id
Результат: models/mart/orders_daily_summary.sql + schema.yml с описаниями столбцов
```

---

## Example 2 — Staging model from raw source

**EN:**
```
/new-model "stg_stripe_payments"

Layer: staging (clean and rename raw Stripe webhook events)
Source: raw.stripe_events table (loaded by Fivetran)
Raw schema: id, type, data (JSON), created (Unix timestamp), livemode
Filter: type IN ('payment_intent.succeeded', 'payment_intent.payment_failed', 'charge.refunded')
Transformations:
  - Parse data JSON: extract payment_intent_id, amount, currency, customer_id, metadata.order_id
  - Convert created (Unix) to timestamp_tz
  - Rename: id → stripe_event_id, amount → amount_cents (keep raw cents)
  - Add derived: amount_usd = amount_cents / 100.0
Materialisation: view (no storage cost; always fresh)
Tests: unique(stripe_event_id), not_null(stripe_event_id, payment_intent_id, created_at)
```

**RU:**
```
/new-model "stg_stripe_payments"

Слой: staging (очистка и переименование сырых Stripe webhook событий)
Источник: таблица raw.stripe_events (загружается Fivetran)
Сырая схема: id, type, data (JSON), created (Unix timestamp), livemode
Фильтр: type IN ('payment_intent.succeeded', 'payment_intent.payment_failed', 'charge.refunded')
Трансформации:
  - Парсинг JSON поля data: извлечь payment_intent_id, amount, currency, customer_id, metadata.order_id
  - Конвертировать created (Unix) в timestamp_tz
  - Переименовать: id → stripe_event_id, amount → amount_cents (оставить сырые центы)
  - Добавить производный: amount_usd = amount_cents / 100.0
Материализация: view (без затрат на хранение; всегда актуально)
Тесты: unique(stripe_event_id), not_null(stripe_event_id, payment_intent_id, created_at)
```

---

## Example 3 — Quick / Intermediate model

**EN:**
```
/new-model "int_user_order_stats"

Layer: intermediate (joins for downstream mart reuse)
Logic: for each user — total_orders, total_spent_usd, first_order_date, last_order_date, days_since_last_order
Sources: stg_orders (already exists), stg_payments (already exists)
Include only: completed orders (status = 'paid')
Materialisation: ephemeral (no table — inlined into mart queries)
No additional tests needed — covered by upstream staging tests
```

**RU:**
```
/new-model "int_user_order_stats"

Слой: intermediate (джойны для переиспользования в mart)
Логика: для каждого пользователя — total_orders, total_spent_usd, first_order_date, last_order_date, days_since_last_order
Источники: stg_orders (уже существует), stg_payments (уже существует)
Включать только: завершённые заказы (status = 'paid')
Материализация: ephemeral (без таблицы — встраивается в mart запросы)
Дополнительные тесты не нужны — покрыты тестами вышестоящего staging слоя
```
