---
workflow: backfill-data
---

# Prompt: `/backfill-data`

Use when: reprocessing historical data after a pipeline fix, schema change, or new metric definition — safely and in batches.

---

## Example 1 — Pipeline fix backfill

**EN:**
```
/backfill-data

Reason: bug fix — revenue calculation excluded refunds for 47 days (2024-07-01 to 2024-08-16)
Affected model: mart.orders_daily_summary (column: gross_revenue_usd)
Fix deployed: 2024-08-17 (current data correct from this date)
Backfill scope: 2024-07-01 → 2024-08-16 (47 days)
Pipeline: Airflow DAG orders_daily_summary_dag
Backfill strategy:
  - Process in 7-day batches (avoid OOM on large joins)
  - Batch order: oldest first (2024-07-01 → 2024-08-16)
  - Run during off-peak hours (02:00–06:00 UTC)
Downstream impact: BI dashboards consume this model — notify analytics team before start
Validation: after backfill, compare gross_revenue_usd SUM for backfill period against Stripe dashboard (expected match within 0.1%)
Idempotency: Airflow dag run with execution_date override; model uses INSERT OVERWRITE partition
```

**RU:**
```
/backfill-data

Причина: исправление бага — расчёт revenue исключал возвраты в течение 47 дней (2024-07-01 по 2024-08-16)
Затронутая модель: mart.orders_daily_summary (столбец: gross_revenue_usd)
Исправление задеплоено: 2024-08-17 (текущие данные корректны с этой даты)
Скоуп бэкфилла: 2024-07-01 → 2024-08-16 (47 дней)
Pipeline: Airflow DAG orders_daily_summary_dag
Стратегия бэкфилла:
  - Обработка пакетами по 7 дней (избежать OOM на больших джойнах)
  - Порядок пакетов: сначала старейшие (2024-07-01 → 2024-08-16)
  - Запуск в нерабочие часы (02:00–06:00 UTC)
Влияние на downstream: BI дашборды используют эту модель — уведомить analytics команду перед началом
Валидация: после бэкфилла сравнить SUM gross_revenue_usd за период бэкфилла со Stripe dashboard (ожидаемое совпадение в пределах 0.1%)
Идемпотентность: Airflow dag run с переопределением execution_date; модель использует INSERT OVERWRITE partition
```

---

## Example 2 — New metric backfill

**EN:**
```
/backfill-data

Reason: new column added to mart.user_cohorts — ltv_90d (90-day lifetime value)
Column exists in model since today, but historical rows have NULL
Backfill scope: all users acquired before 2024-09-01 (need 90 days of order history to compute)
Data available: stg_orders has full history back to 2022-01-01
Strategy: single batch UPDATE using window function (manageable — 2M rows, < 5 min on ClickHouse)
Downtime risk: UPDATE on columnar store — run during low-traffic window
Validation: ltv_90d distribution should match manual Stripe cohort analysis (±5%)
Rollback: snapshot table before UPDATE → mart.user_cohorts_backup_20240915
```

**RU:**
```
/backfill-data

Причина: новый столбец добавлен в mart.user_cohorts — ltv_90d (lifetime value за 90 дней)
Столбец существует в модели с сегодняшнего дня, но исторические строки имеют NULL
Скоуп бэкфилла: все пользователи привлечённые до 2024-09-01 (нужно 90 дней истории заказов для расчёта)
Доступные данные: stg_orders имеет полную историю начиная с 2022-01-01
Стратегия: единовременный UPDATE с оконной функцией (управляемо — 2M строк, < 5 мин на ClickHouse)
Риск простоя: UPDATE на колоночном хранилище — запускать в окно низкого трафика
Валидация: распределение ltv_90d должно соответствовать ручному анализу когорт Stripe (±5%)
Откат: снапшот таблицы до UPDATE → mart.user_cohorts_backup_20240915
```

---

## Example 3 — Quick / Partition reprocess

**EN:**
```
/backfill-data

Reason: Kafka consumer lag caused 3 hours of missing events (2024-09-10 14:00–17:00 UTC)
Events are available in DLQ — need to replay into raw.user_events
Scope: single 3-hour partition (date=2024-09-10, hour IN (14,15,16))
Method: replay from DLQ topic user_events_dlq → raw.user_events; downstream dbt models will auto-refresh
Estimated volume: ~180 000 events (normal: 60k/hr)
Validation: raw.user_events row count for affected hours matches DLQ message count
```

**RU:**
```
/backfill-data

Причина: задержка Kafka consumer привела к 3 часам пропущенных событий (2024-09-10 14:00–17:00 UTC)
События доступны в DLQ — нужно воспроизвести в raw.user_events
Скоуп: одна 3-часовая партиция (date=2024-09-10, hour IN (14,15,16))
Метод: воспроизведение из DLQ топика user_events_dlq → raw.user_events; downstream dbt модели обновятся автоматически
Ожидаемый объём: ~180 000 событий (норма: 60k/ч)
Валидация: количество строк raw.user_events для затронутых часов совпадает с количеством сообщений DLQ
```
