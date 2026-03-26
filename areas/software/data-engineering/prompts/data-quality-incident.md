---
workflow: data-quality-incident
---

# Prompt: `/data-quality-incident`

Use when: a data quality issue is detected — wrong numbers in dashboards, failed dbt tests, or downstream consumer complaints — and needs systematic triage and remediation.

---

## Example 1 — Metric discrepancy in BI dashboard

**EN:**
```
/data-quality-incident

Incident: revenue metric in Looker dashboard shows $2.1M for August; finance team confirms actual = $2.4M (14% discrepancy)
Detected: today (2024-09-02) by Finance during month-end close
Impact: August MBR already sent with wrong numbers; investor deck in preparation
Affected metric: gross_revenue_usd in mart.orders_daily_summary
Last known correct: July revenue validated correctly
Changes since July:
  - currency normalisation refactored (PR #287, merged 2024-08-03)
  - Stripe webhook consumer updated (PR #291, merged 2024-08-09)
Immediate action: quarantine August data — add warning banner in Looker dashboard
Investigation priority: compare mart revenue vs. Stripe dashboard daily for August; identify date of divergence
Output: root cause identified, corrected August numbers, fix deployed, stakeholder communication
```

**RU:**
```
/data-quality-incident

Инцидент: метрика revenue в Looker дашборде показывает $2.1M за август; финансовая команда подтверждает фактическое = $2.4M (расхождение 14%)
Обнаружено: сегодня (2024-09-02) Финансами во время закрытия месяца
Влияние: MBR за август уже отправлен с неверными цифрами; готовится презентация для инвесторов
Затронутая метрика: gross_revenue_usd в mart.orders_daily_summary
Последний известный корректный: revenue за июль валидирован корректно
Изменения с июля:
  - рефакторинг нормализации валюты (PR #287, слит 2024-08-03)
  - обновлён Stripe webhook consumer (PR #291, слит 2024-08-09)
Немедленное действие: карантин данных за август — добавить предупреждение в Looker дашборд
Приоритет расследования: сравнить mart revenue vs. Stripe dashboard посуточно за август; определить дату расхождения
Результат: корневая причина определена, скорректированные цифры за август, исправление задеплоено, коммуникация стейкхолдеров
```

---

## Example 2 — dbt test failure in CI

**EN:**
```
/data-quality-incident

Incident: dbt CI run failed — 3 tests failing on morning run (2024-09-15 07:14 UTC)
Failed tests:
  - not_null — stg_orders.user_id: 847 NULL values (was 0 yesterday)
  - unique — mart.orders_daily_summary.order_date+country: 12 duplicate rows
  - accepted_values — stg_payments.status: unexpected value "pending_review" found
Affected DAG: orders pipeline (blocked — downstream models not running)
Data freshness: last successful run 2024-09-14 03:00 UTC
Possible cause: Fivetran schema change — new NULL rule relaxed upstream; new payment status added by payment team
Urgency: dashboards stale; finance report due at 12:00 UTC (4.5 hours)
Immediate: unblock critical models (orders_daily_summary) while investigating nullable user_id
```

**RU:**
```
/data-quality-incident

Инцидент: CI запуск dbt завершился с ошибкой — 3 упавших теста на утреннем запуске (2024-09-15 07:14 UTC)
Упавшие тесты:
  - not_null — stg_orders.user_id: 847 NULL значений (вчера было 0)
  - unique — mart.orders_daily_summary.order_date+country: 12 дублирующихся строк
  - accepted_values — stg_payments.status: найдено неожиданное значение "pending_review"
Затронутый DAG: pipeline orders (заблокирован — downstream модели не запускаются)
Свежесть данных: последний успешный запуск 2024-09-14 03:00 UTC
Возможная причина: изменение схемы Fivetran — новое правило NULL ослаблено upstream; новый статус платежа добавлен payment командой
Срочность: дашборды устаревшие; финансовый отчёт ожидается в 12:00 UTC (через 4.5 часа)
Немедленно: разблокировать критические модели (orders_daily_summary) пока расследуем nullable user_id
```

---

## Example 3 — Quick / Duplicate records detected

**EN:**
```
/data-quality-incident

Issue: mart.user_cohorts has duplicate user_id rows (unique test added today — was missing)
Scope: 2 341 duplicate user_ids out of 840 000 total (0.28%)
Root cause suspected: missing DISTINCT in stg_users CTE — users with multiple email verifications
Impact: downstream: cohort analysis double-counts affected users; LTV metrics inflated by ~0.3%
Fix: add DISTINCT on user_id to stg_users, re-run mart.user_cohorts
Priority: medium (small %, dashboard numbers within acceptable tolerance)
```

**RU:**
```
/data-quality-incident

Проблема: mart.user_cohorts содержит дублирующиеся строки user_id (unique тест добавлен сегодня — ранее отсутствовал)
Скоуп: 2 341 дублирующихся user_id из 840 000 всего (0.28%)
Предполагаемая причина: отсутствие DISTINCT в CTE stg_users — пользователи с несколькими подтверждениями email
Влияние: downstream: анализ когорт двойной подсчёт затронутых пользователей; LTV метрики завышены на ~0.3%
Исправление: добавить DISTINCT на user_id в stg_users, перезапустить mart.user_cohorts
Приоритет: средний (маленький %, цифры дашборда в пределах допустимого отклонения)
```
