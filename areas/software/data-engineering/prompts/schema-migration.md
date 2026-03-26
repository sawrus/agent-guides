---
workflow: schema-migration
---

# Prompt: `/schema-migration`

Use when: applying a breaking or non-breaking schema change to a data warehouse or dbt source — using expand/contract to avoid downstream breakage.

---

## Example 1 — Breaking column rename (expand/contract)

**EN:**
```
/schema-migration

Change: rename column revenue → gross_revenue_usd in raw.orders (BigQuery)
Breaking: YES — 12 downstream dbt models reference "revenue" directly
Strategy: expand/contract
  Phase 1 (Expand): add new column gross_revenue_usd (copy of revenue); keep revenue; deploy dbt models to use gross_revenue_usd
  Phase 2 (Validate): run 7-day parallel validation — SUM(revenue) = SUM(gross_revenue_usd) per day
  Phase 3 (Contract): drop column revenue after all downstream models migrated and validated
Timeline: Phase 1 this sprint; Phase 3 next sprint (safe window)
Downstream models: models/staging/stg_orders.sql, models/mart/orders_daily.sql (+ 10 others — list attached)
Stakeholder notification: analytics team must update any direct SQL queries against raw.orders
```

**RU:**
```
/schema-migration

Изменение: переименование столбца revenue → gross_revenue_usd в raw.orders (BigQuery)
Breaking: ДА — 12 downstream dbt моделей ссылаются на "revenue" напрямую
Стратегия: expand/contract
  Фаза 1 (Expand): добавить новый столбец gross_revenue_usd (копия revenue); оставить revenue; задеплоить dbt модели на использование gross_revenue_usd
  Фаза 2 (Validate): запустить 7-дневную параллельную валидацию — SUM(revenue) = SUM(gross_revenue_usd) за день
  Фаза 3 (Contract): удалить столбец revenue после миграции и валидации всех downstream моделей
Timeline: Фаза 1 в этом спринте; Фаза 3 в следующем спринте (безопасное окно)
Downstream модели: models/staging/stg_orders.sql, models/mart/orders_daily.sql (+ 10 других — список приложен)
Уведомление стейкхолдеров: analytics команда должна обновить любые прямые SQL запросы к raw.orders
```

---

## Example 2 — Non-breaking new column

**EN:**
```
/schema-migration

Change: add column acquisition_channel (VARCHAR(50), nullable) to raw.users
Source: Fivetran CRM connector — new field available from 2024-09-01
Breaking: NO — additive change; existing queries unaffected
Migration steps:
  1. Confirm Fivetran sync picks up new field (check schema in Fivetran UI)
  2. Add column to stg_users.sql SELECT and schema.yml documentation
  3. Add acquisition_channel to mart.user_cohorts grouping (new dimension)
  4. Backfill: historical rows will be NULL (field not available before 2024-09-01)
  5. Add dbt test: accepted_values(organic, paid_search, referral, social, direct, unknown)
Downstream impact: mart.user_cohorts will have new column — notify BI team to add to dashboards
```

**RU:**
```
/schema-migration

Изменение: добавление столбца acquisition_channel (VARCHAR(50), nullable) в raw.users
Источник: Fivetran CRM коннектор — новое поле доступно с 2024-09-01
Breaking: НЕТ — аддитивное изменение; существующие запросы не затронуты
Шаги миграции:
  1. Убедиться что Fivetran sync подхватывает новое поле (проверить схему в Fivetran UI)
  2. Добавить acquisition_channel в SELECT stg_users.sql и документацию schema.yml
  3. Добавить acquisition_channel в группировку mart.user_cohorts (новое измерение)
  4. Бэкфилл: исторические строки будут NULL (поле недоступно до 2024-09-01)
  5. Добавить dbt тест: accepted_values(organic, paid_search, referral, social, direct, unknown)
Влияние на downstream: mart.user_cohorts получит новый столбец — уведомить BI команду для добавления в дашборды
```

---

## Example 3 — Type change (breaking)

**EN:**
```
/schema-migration

Change: order_id column type VARCHAR(36) → BIGINT in raw.orders
Reason: source system migrated from UUID to integer IDs
Breaking: YES — all downstream models cast or join on order_id as string
Strategy:
  1. Add order_id_new BIGINT column alongside VARCHAR order_id
  2. Populate order_id_new for new records; historical UUIDs map to NULL (no integer equivalent)
  3. Update all downstream models to use order_id_new with COALESCE(order_id_new, order_id) during transition
  4. After 30 days, rename order_id_new → order_id; archive old VARCHAR column
Historical records: ~3M orders with UUID order_id — will retain VARCHAR; only new orders get BIGINT
```

**RU:**
```
/schema-migration

Изменение: тип столбца order_id VARCHAR(36) → BIGINT в raw.orders
Причина: исходная система перешла с UUID на целочисленные ID
Breaking: ДА — все downstream модели приводят или джойнят order_id как строку
Стратегия:
  1. Добавить столбец order_id_new BIGINT рядом с VARCHAR order_id
  2. Заполнить order_id_new для новых записей; исторические UUID маппируются в NULL (нет целочислового эквивалента)
  3. Обновить все downstream модели для использования order_id_new с COALESCE(order_id_new, order_id) в период перехода
  4. Через 30 дней, переименовать order_id_new → order_id; архивировать старый VARCHAR столбец
Исторические записи: ~3M заказов с UUID order_id — сохранят VARCHAR; только новые заказы получат BIGINT
```
