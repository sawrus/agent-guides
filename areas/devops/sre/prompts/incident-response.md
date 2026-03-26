---
workflow: incident-response
---

# Prompt: `/incident-response`

Use when: actively responding to a production incident or resilience event that demands mitigation, communication, and a clear escalation path.

---

## Example 1 — P0 service outage

**EN:**
```
/incident-response

Severity: P0
Service: order-service / Namespace: production
Symptom: complete service outage — 100% error rate since 15:42 UTC
Affected: all checkout flows; estimated 2,000 users/min impact
IC: @me (on-call)
Available data:
  - Alert fired: HighErrorRate 100% for order-service
  - Recent deploy: order-service v3.1.0 at 15:38 UTC (4 min before incident)
  - Prometheus shows: all pods Running but 0 successful responses
  - Logs show: "connection refused" to postgres-primary:5432
Actions needed:
  1. Immediate mitigation options (rollback, feature flag, scale)
  2. Status page template for this incident
  3. Slack communication template for #incidents
  4. Scribe doc started
```

**RU:**
```
/incident-response

Severity: P0
Сервис: order-service / Namespace: production
Симптом: полный отказ сервиса — 100% error rate с 15:42 UTC
Затронуто: все checkout flow; ~2,000 пользователей/мин
IC: @я (on-call)
Доступные данные:
  - Алерт: HighErrorRate 100% для order-service
  - Последний деплой: order-service v3.1.0 в 15:38 UTC (за 4 мин до инцидента)
  - Prometheus: все поды Running но 0 успешных ответов
  - Логи: "connection refused" на postgres-primary:5432
Необходимые действия:
  1. Варианты немедленной митигации (откат, feature flag, масштабирование)
  2. Шаблон для status page по этому инциденту
  3. Шаблон Slack сообщения для #incidents
  4. Начат scribe doc
```

---

## Example 2 — P1 performance degradation

**EN:**
```
/incident-response

Severity: P1
Service: payment-service / Namespace: production
Symptom: p99 latency spiked from 200ms to 4.2s; error rate 0.8% (below 1% threshold but rising)
Affected: ~15% of payment requests timing out; no complete outage
Recent changes: database index migration ran at 03:00 UTC (8h ago)
Metrics: CPU normal, memory normal, DB connections at 89% pool capacity
Action needed:
  1. Classify: is this trending toward P0? (burn rate calculation)
  2. Identify: DB connection exhaustion vs slow query vs external dependency
  3. Quick mitigation options that don't require deploy
  4. Comms: notify on Slack (not status page yet — degraded only)
```

**RU:**
```
/incident-response

Severity: P1
Сервис: payment-service / Namespace: production
Симптом: p99 latency вырос с 200ms до 4.2s; error rate 0.8% (ниже порога 1% но растёт)
Затронуто: ~15% запросов на оплату с таймаутом; полного отказа нет
Недавние изменения: миграция индекса БД в 03:00 UTC (8ч назад)
Метрики: CPU в норме, память в норме, DB connections на 89% от pool capacity
Необходимые действия:
  1. Классификация: движется ли это к P0? (расчёт burn rate)
  2. Определить: исчерпание DB connections vs медленный запрос vs внешняя зависимость
  3. Варианты быстрой митигации без деплоя
  4. Коммуникация: уведомить в Slack (не status page пока — только деградация)
```

---

## Example 3 — Network partition: database failover test

**EN:**
```
/incident-response

System under test: payment-service → postgres-primary (CloudNativePG cluster)
Hypothesis: "payment-service automatically reconnects within 30s after postgres primary failover, with < 500ms added latency per request during reconnect"
Experiment:
  - Inject NetworkChaos: block traffic from payment-service pods to postgres-primary for 90s
  - CloudNativePG should auto-promote replica to primary during network partition
  - Monitor: payment-service error rate, connection pool exhaustion (pgbouncer stats), reconnect time
  - Verify: after partition heals, service recovers automatically (no manual intervention)
Pre-conditions:
  - Confirm postgres replica is healthy before starting
  - Confirm pgbouncer reconnect_timeout is set appropriately
  - Run at 10% of normal traffic (k6 load generator)
```

**RU:**
```
/incident-response

Система под тестом: payment-service → postgres-primary (CloudNativePG кластер)
Гипотеза: "payment-service автоматически переподключается в течение 30с после failover postgres primary, с задержкой < 500ms на запрос во время переподключения"
Эксперимент:
  - Инжектировать NetworkChaos: блокировать трафик от подов payment-service к postgres-primary на 90с
  - CloudNativePG должен автоматически назначить реплику primary во время сетевого раздела
  - Мониторинг: error rate payment-service, исчерпание connection pool (статистика pgbouncer), время переподключения
  - Проверить: после восстановления раздела сервис восстанавливается автоматически (без ручного вмешательства)
Предусловия:
  - Убедиться что postgres реплика здорова перед началом
  - Убедиться что pgbouncer reconnect_timeout настроен правильно
  - Запустить при 10% от нормального трафика (k6 генератор нагрузки)
```
