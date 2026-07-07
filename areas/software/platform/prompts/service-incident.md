---
workflow: service-incident
---

# Prompt: `/service-incident`

Use when: a production incident is active — to coordinate triage, mitigation, communication, and postmortem.

---

## Example 1 — P1 service outage

**EN:**
```
/service-incident

Severity: P1 — complete service outage
Affected: checkout flow (POST /api/v1/orders returns 503 for 100% of requests)
Started: 14:32 UTC (23 minutes ago)
Alert source: PagerDuty alert "order-service error rate 100%" + customer reports in Slack #support
Initial observations:
  - order-service pods restarting every 30 seconds (CrashLoopBackOff)
  - Last deploy: order-service v2.6.1 — deployed 14:28 UTC (4 min before incident)
  - DB: PostgreSQL healthy (no alerts), connection pool normal
  - Error in logs: "FATAL: relation 'order_status_history' does not exist"
Incident channel: #inc-2024-09-15-orders (already created)
On-call: @alice (primary), @bob (secondary)
Status page: needs update — "investigating checkout issues"
```

**RU:**
```
/service-incident

Серьёзность: P1 — полный отказ сервиса
Затронуто: поток оформления заказа (POST /api/v1/orders возвращает 503 для 100% запросов)
Начало: 14:32 UTC (23 минуты назад)
Источник алерта: PagerDuty алерт "order-service error rate 100%" + жалобы клиентов в Slack #support
Начальные наблюдения:
  - Поды order-service перезапускаются каждые 30 секунд (CrashLoopBackOff)
  - Последний деплой: order-service v2.6.1 — задеплоен в 14:28 UTC (за 4 мин до инцидента)
  - БД: PostgreSQL здоров (нет алертов), connection pool в норме
  - Ошибка в логах: "FATAL: relation 'order_status_history' does not exist"
Канал инцидента: #inc-2024-09-15-orders (уже создан)
Дежурные: @alice (основной), @bob (вторичный)
Status page: требует обновления — "расследуем проблемы с оформлением заказов"
```

---

## Example 2 — P2 performance degradation

**EN:**
```
/service-incident

Severity: P2 — severe performance degradation (not full outage)
Affected: product search — p99 latency 8s (baseline: 120ms); timeout errors at 12%
Started: ~11:00 UTC (gradual, no single deploy triggered it)
Observations:
  - Only search endpoints affected; orders, auth, payments normal
  - Elasticsearch CPU at 94% (normal: 30%)
  - Spike in search traffic: 3x normal (Monday morning, promotional email sent at 10:45 UTC)
  - No recent code changes to search module
Hypothesis: Elasticsearch overwhelmed by traffic spike; may need circuit breaker
Workaround available: disable real-time index refresh (performance mode) — data lag 60s acceptable
Impact: users see slow search results; purchase flow unaffected
Communication: notify #product (not public status page — not full outage)
```

**RU:**
```
/service-incident

Серьёзность: P2 — серьёзная деградация производительности (не полный отказ)
Затронуто: поиск продуктов — p99 задержка 8s (baseline: 120ms); ошибки таймаута 12%
Начало: ~11:00 UTC (постепенное, не вызвано одним деплоем)
Наблюдения:
  - Затронуты только эндпоинты поиска; заказы, auth, платежи в норме
  - CPU Elasticsearch на 94% (норма: 30%)
  - Всплеск поискового трафика: 3x нормального (утро понедельника, промо email отправлен в 10:45 UTC)
  - Нет недавних изменений кода в модуле поиска
Гипотеза: Elasticsearch перегружен всплеском трафика; возможно нужен circuit breaker
Временное решение: отключить real-time обновление индекса (режим производительности) — задержка данных 60s приемлема
Влияние: пользователи видят медленные результаты поиска; поток покупки не затронут
Коммуникация: уведомить #product (не публичная status page — не полный отказ)
```

---

## Example 3 — Quick / Post-incident postmortem

**EN:**
```
/service-incident

Mode: postmortem (incident resolved — INC-2024-142 checkout outage, duration 34 min)
Timeline: already documented in incident channel
Root cause: DB migration in v2.6.1 created new table but deploy ran before migration (race condition in CI)
Action items needed:
  - Pre-deploy migration check (block deploy if pending migrations)
  - Smoke test in canary phase checks table existence
  - Runbook update: rollback procedure for failed migrations
Format: blameless postmortem per Google SRE template
Due: draft to team within 48h
```

**RU:**
```
/service-incident

Режим: postmortem (инцидент разрешён — INC-2024-142 отказ оформления заказа, длительность 34 мин)
Таймлайн: уже задокументирован в канале инцидента
Корневая причина: миграция БД в v2.6.1 создала новую таблицу но деплой запустился до миграции (race condition в CI)
Необходимые action items:
  - Проверка миграции перед деплоем (блокировать деплой если есть ожидающие миграции)
  - Smoke test на этапе canary проверяет существование таблицы
  - Обновление runbook: процедура отката для неудачных миграций
Формат: blameless postmortem по шаблону Google SRE
Срок: черновик команде в течение 48ч
```
