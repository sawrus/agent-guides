---
workflow: onboard-service-monitoring
---

# Prompt: `/onboard-service-monitoring`

Use when: adding observability (metrics, logs, traces, alerts, dashboard) to a service.

---

## Example 1 — Full observability stack for Python service

**EN:**
```
/onboard-service-monitoring

Service: checkout-service / Namespace: production / Language: Python 3.12 + FastAPI
Current state: service runs, zero observability
Stack: Prometheus (kube-prometheus-stack) + Loki + Tempo + Grafana
Required:
  - Metrics: prometheus-client; expose /metrics; golden signals (latency, errors, traffic, saturation)
  - Traces: opentelemetry-sdk auto-instrumentation; export to otel-collector:4317
  - Logs: already JSON; add trace_id injection via TraceContextFilter
  - ServiceMonitor: scrape interval 15s
  - Alerts: HighErrorRate (critical > 1%), HighP99Latency (warning > 1s), PodMemoryPressure (warning > 85%)
  - Dashboard: standard service overview + business metric: checkout_conversion_rate
Business metric to add: checkout_success_total / checkout_attempt_total (gauge panel)
```

**RU:**
```
/onboard-service-monitoring

Сервис: checkout-service / Namespace: production / Язык: Python 3.12 + FastAPI
Текущее состояние: сервис работает, нет observability
Стек: Prometheus (kube-prometheus-stack) + Loki + Tempo + Grafana
Требуется:
  - Метрики: prometheus-client; /metrics endpoint; golden signals (latency, errors, traffic, saturation)
  - Трейсы: opentelemetry-sdk авто-инструментирование; экспорт на otel-collector:4317
  - Логи: уже JSON; добавить инжекцию trace_id через TraceContextFilter
  - ServiceMonitor: интервал scrape 15с
  - Алерты: HighErrorRate (critical > 1%), HighP99Latency (warning > 1s), PodMemoryPressure (warning > 85%)
  - Dashboard: стандартный обзор сервиса + бизнес-метрика: checkout_conversion_rate
Бизнес-метрика: checkout_success_total / checkout_attempt_total (gauge панель)
```

---

## Example 2 — Alerts-only for existing service

**EN:**
```
/onboard-service-monitoring

Service: notification-service / Namespace: production
Current state: metrics already scraped (ServiceMonitor exists); no alerts defined
Task: add alerting only
Required alerts:
  - HighErrorRate: critical if error rate > 1% for 2m
  - QueueBacklog: warning if notification_queue_depth > 1000 for 5m (custom metric already exposed)
  - PodRestarting: warning if pod restarts > 3 in 15m
Each alert: runbook_url pointing to docs/runbooks/<alert-name>.md (create stub runbooks too)
Alertmanager routing: critical → PagerDuty; warning → #alerts-warning Slack
```

**RU:**
```
/onboard-service-monitoring

Сервис: notification-service / Namespace: production
Текущее состояние: метрики уже собираются (ServiceMonitor есть); алерты не настроены
Задача: только настройка алертов
Необходимые алерты:
  - HighErrorRate: critical при error rate > 1% в течение 2м
  - QueueBacklog: warning при notification_queue_depth > 1000 в течение 5м (кастомная метрика уже доступна)
  - PodRestarting: warning при рестартах пода > 3 за 15м
Каждый алерт: runbook_url → docs/runbooks/<alert-name>.md (создать stub runbooks тоже)
Маршрутизация Alertmanager: critical → PagerDuty; warning → #alerts-warning Slack
```
