---
workflow: alert-investigation
---

# Prompt: `/alert-investigation`

Use when: investigating a firing alert, burn-rate anomaly, or correlated trace/log signal to determine root cause and mitigation.

---

## Example 1 — HighErrorRate firing in production

**EN:**
```
/alert-investigation

Alert: HighErrorRate / Service: payment-service / Namespace: production
Fired at: 2024-11-15 03:42 UTC / Current error rate: 4.2% (threshold: 1%)
Error type: HTTP 502 (Bad Gateway from upstream)
Available data:
  - Prometheus: http_requests_total labels available
  - Logs: Loki, JSON structured, trace_id present
  - Traces: Tempo available
  - Recent changes: payment-service v2.4.1 deployed 20 min ago
Investigation steps:
  1. Identify which endpoint(s) are erroring (PromQL breakdown by path)
  2. Correlate with deployment time
  3. Check logs for upstream call errors (trace_id → Tempo for full trace)
  4. Determine: rollback v2.4.0 or hotfix?
```

**RU:**
```
/alert-investigation

Алерт: HighErrorRate / Сервис: payment-service / Namespace: production
Сработал: 2024-11-15 03:42 UTC / Текущий error rate: 4.2% (порог: 1%)
Тип ошибок: HTTP 502 (Bad Gateway от upstream)
Доступные данные:
  - Prometheus: метрики http_requests_total с labels
  - Логи: Loki, JSON, trace_id присутствует
  - Трейсы: Tempo доступен
  - Последние изменения: payment-service v2.4.1 задеплоен 20 мин назад
Шаги расследования:
  1. Определить какие endpoint(ы) ошибаются (PromQL разбивка по path)
  2. Сопоставить со временем деплоя
  3. Проверить логи на ошибки вызова upstream (trace_id → Tempo для полного трейса)
  4. Решить: откатить до v2.4.0 или сделать hotfix?
```

---

## Example 2 — Alert fatigue investigation (too many false positives)

**EN:**
```
/alert-investigation

Problem: PodMemoryPressure alert fires 8-12 times per week for ml-worker pods but engineers stop acting on it
Current threshold: memory > 85% for 5m
Context: ml-worker has bursty memory usage (spikes to 90% during batch, then drops)
Goal: reduce false positive rate without missing real OOM risk
Analysis needed:
  1. Query actual OOMKill events in last 30 days (kube_pod_container_status_last_terminated_reason)
  2. Correlate memory spike timing with batch job schedule
  3. Propose new threshold or alerting strategy (e.g. rate-of-change instead of absolute)
  4. Update PrometheusRule + runbook
```

**RU:**
```
/alert-investigation

Проблема: алерт PodMemoryPressure срабатывает 8-12 раз в неделю для ml-worker подов, но инженеры перестали реагировать
Текущий порог: memory > 85% в течение 5м
Контекст: ml-worker имеет взрывное использование памяти (пики до 90% во время batch, потом падает)
Цель: снизить число false positive без пропуска реального риска OOM
Необходимый анализ:
  1. Запросить реальные события OOMKill за последние 30 дней (kube_pod_container_status_last_terminated_reason)
  2. Сопоставить время пиков памяти с расписанием batch job
  3. Предложить новый порог или стратегию алертинга (например, rate-of-change вместо абсолютного значения)
  4. Обновить PrometheusRule + runbook
```

---

## Example 3 — Trace slow checkout (multi-service waterfall)

**EN:**
```
/alert-investigation

Symptom: checkout p99 latency = 3.2s; SLO threshold = 500ms
Trace available: trace_id=abc123def456 (found in Loki error log, captured during slow request)
Services in trace: api-gateway → checkout-service → payment-service → order-service → postgres
Goal:
  1. Open trace in Tempo; identify which span is slow
  2. Check for: sequential calls that could be parallelised, N+1 DB queries, missing DB indexes
  3. If DB span is slow: correlate with postgres slow query log (Loki query by trace_id)
  4. Output: root cause span + recommended fix (code change or index)
Tempo URL: https://tempo.monitoring.internal
```

**RU:**
```
/alert-investigation

Симптом: checkout p99 latency = 3.2s; порог SLO = 500ms
Трейс доступен: trace_id=abc123def456 (найден в Loki error log, захвачен во время медленного запроса)
Сервисы в трейсе: api-gateway → checkout-service → payment-service → order-service → postgres
Цель:
  1. Открыть трейс в Tempo; определить какой span медленный
  2. Проверить: последовательные вызовы которые можно распараллелить, N+1 DB запросы, отсутствующие индексы
  3. Если медленный DB span: сопоставить с postgres slow query log (запрос Loki по trace_id)
  4. Результат: корневой медленный span + рекомендуемое исправление (изменение кода или индекс)
Tempo URL: https://tempo.monitoring.internal
```
