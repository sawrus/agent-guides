---
workflow: lineage-trace
---

# Prompt: `/lineage-trace`

Use when: tracing the full upstream and downstream lineage of a dataset, column, or metric — to assess the blast radius of a change, investigate a data quality issue, or document data provenance.

---

## Example 1 — Blast radius analysis before a change

**EN:**
```
/lineage-trace

Direction: downstream (what will break if I change this?)
Target: dbt model stg_orders (column: status)
Proposed change: add new status value "partially_refunded" to accepted_values
Trace depth: full — all downstream models, dashboards, and consumers
Environment: dbt project (dbt Cloud), Looker BI, Kafka downstream consumers
Expected graph:
  stg_orders → int_order_aggregates → mart.orders_daily_summary → mart.user_cohorts
                                     → mart.revenue_by_channel
                                     → Looker Explore: "Orders"
  stg_orders → Kafka topic: order_status_events → notification-service (consume)
Identify: which models have accepted_values test on status (will fail if not updated);
          which Looker dashboards filter on status values; which consumers handle status transitions
Output: lineage-impact-report.md with change checklist per affected node
```

**RU:**
```
/lineage-trace

Направление: downstream (что сломается если изменить это?)
Цель: dbt модель stg_orders (столбец: status)
Предлагаемое изменение: добавить новое значение статуса "partially_refunded" в accepted_values
Глубина трассировки: полная — все downstream модели, дашборды и потребители
Окружение: dbt проект (dbt Cloud), Looker BI, Kafka downstream потребители
Ожидаемый граф:
  stg_orders → int_order_aggregates → mart.orders_daily_summary → mart.user_cohorts
                                     → mart.revenue_by_channel
                                     → Looker Explore: "Orders"
  stg_orders → Kafka топик: order_status_events → notification-service (потребление)
Определить: какие модели имеют тест accepted_values на status (упадут если не обновить);
            какие Looker дашборды фильтруют по значениям status; какие потребители обрабатывают переходы статусов
Результат: lineage-impact-report.md с чеклистом изменений для каждого затронутого узла
```

---

## Example 2 — Root cause trace for a data quality issue

**EN:**
```
/lineage-trace

Direction: upstream (where does this bad data come from?)
Target: mart.orders_daily_summary — column gross_revenue_usd shows 14% lower than expected for August
Trace upstream from: mart.orders_daily_summary
Intermediate models: int_order_financials → stg_orders, stg_payments, stg_exchange_rates
Source tables: raw.stripe_events (Fivetran), raw.orders (app DB replica)
Investigation steps:
  1. Check gross_revenue_usd at each layer: raw → staging → intermediate → mart
  2. Find the layer where discrepancy first appears
  3. Check if stg_exchange_rates has correct rates for August (EUR→USD rate changed significantly in August)
  4. Check stg_payments filter — are refunds being excluded or double-counted?
Output: layer-by-layer discrepancy table; identified transformation step where values diverge
```

**RU:**
```
/lineage-trace

Направление: upstream (откуда берутся эти плохие данные?)
Цель: mart.orders_daily_summary — столбец gross_revenue_usd показывает на 14% меньше ожидаемого за август
Трассировка upstream от: mart.orders_daily_summary
Промежуточные модели: int_order_financials → stg_orders, stg_payments, stg_exchange_rates
Исходные таблицы: raw.stripe_events (Fivetran), raw.orders (реплика app DB)
Шаги расследования:
  1. Проверить gross_revenue_usd на каждом слое: raw → staging → intermediate → mart
  2. Найти слой где впервые появляется расхождение
  3. Проверить есть ли в stg_exchange_rates корректные курсы за август (курс EUR→USD существенно изменился в августе)
  4. Проверить фильтр stg_payments — возвраты исключаются или учитываются дважды?
Результат: таблица расхождений по слоям; определённый шаг трансформации где значения расходятся
```

---

## Example 3 — Compliance / data provenance audit

**EN:**
```
/lineage-trace

Purpose: GDPR Article 30 audit — document where user PII flows in our data platform
Starting point: raw.users (source of truth for PII: email, name, phone)
Trace: all models and tables that contain or derive from PII fields (email, user_id, name, phone)
Include: dbt models, BI exports, data shares, ML feature store
Flag: any PII that reaches:
  - External BI tools (Looker, Metabase) — must confirm row-level security in place
  - ML training datasets — must confirm pseudonymisation or removal
  - Cold storage / archives — must confirm retention policy enforced
Output: PII lineage map (mermaid diagram) + compliance checklist per destination
```

**RU:**
```
/lineage-trace

Назначение: аудит GDPR Статья 30 — задокументировать куда PII пользователей попадает в нашей data платформе
Начальная точка: raw.users (источник истины для PII: email, имя, телефон)
Трассировать: все модели и таблицы которые содержат или являются производными от PII полей (email, user_id, имя, телефон)
Включить: dbt модели, BI экспорты, data shares, ML feature store
Отметить: любой PII который достигает:
  - Внешние BI инструменты (Looker, Metabase) — подтвердить наличие row-level security
  - ML обучающие датасеты — подтвердить псевдоанонимизацию или удаление
  - Холодное хранилище / архивы — подтвердить соблюдение политики хранения
Результат: карта PII lineage (mermaid диаграмма) + чеклист соответствия для каждого назначения
```
