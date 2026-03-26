---
workflow: performance-audit
---

# Prompt: `/performance-audit`

Use when: investigating latency regressions or establishing performance baselines.

---

## Example 1 — Regression investigation

**EN:**
```
/performance-audit

Target: POST /api/v1/orders
Test type: load test
SLO baseline: p95 < 300ms, p99 < 1000ms, error rate < 0.5%
Current p99: 2.4s (regression vs. last release 340ms)
Suspected cause: migration added 3 new FK lookups on order creation
Load profile: ramp to 100 VUs over 2 min, hold 5 min
Environment: staging (isolated from other traffic)
```

**RU:**
```
/performance-audit

Цель: POST /api/v1/orders
Тип теста: нагрузочный тест
SLO baseline: p95 < 300ms, p99 < 1000ms, error rate < 0.5%
Текущий p99: 2.4s (регрессия vs. предыдущий релиз 340ms)
Предполагаемая причина: миграция добавила 3 новых FK lookup при создании заказа
Профиль нагрузки: rampe to 100 VU за 2 мин, держать 5 мин
Окружение: staging (изолировано от другого трафика)
```

---

## Example 2 — Baseline establishment

**EN:**
```
/performance-audit

Target: checkout flow end-to-end (browse → cart → payment → confirmation)
Test type: load + soak
Purpose: establish baselines before Black Friday traffic planning
Load: 500 concurrent users (3x normal peak)
Soak: 2 hours at 200 VUs to detect memory leaks
Output: performance-baselines.json for CI threshold gates
```

**RU:**
```
/performance-audit

Цель: end-to-end поток оформления заказа (просмотр → корзина → оплата → подтверждение)
Тип теста: нагрузочный + soak
Цель: установить baseline перед планированием трафика Black Friday
Нагрузка: 500 одновременных пользователей (3x нормального пика)
Soak: 2 часа при 200 VU для обнаружения утечек памяти
Результат: performance-baselines.json для пороговых значений в CI
```
