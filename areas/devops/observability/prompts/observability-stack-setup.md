---
workflow: observability-stack-setup
---

# Prompt: `/observability-stack-setup`

Use when: setting up the full observability stack from scratch on a K8s cluster.

---

## Example 1 — Full kube-prometheus-stack + Loki + Tempo

**EN:**
```
/observability-stack-setup

Cluster: prod-cluster-eu (bare-metal K8s 1.31, Cilium)
Storage: Longhorn (block storage available)
Stack to deploy (all via Helm + ArgoCD):
  - kube-prometheus-stack (Prometheus + Alertmanager + Grafana + node-exporter + kube-state-metrics)
  - Loki (single binary mode for start; distributed when logs > 50GB/day)
  - Promtail DaemonSet (log collection from all pods)
  - Tempo (distributed tracing, single binary)
  - OpenTelemetry Collector (DaemonSet, receives OTLP)
  - Grafana datasources: Prometheus + Loki + Tempo (auto-configured)
Persistence:
  - Prometheus: 50Gi Longhorn, 15-day retention
  - Loki: 100Gi Longhorn, 30-day retention
  - Tempo: 50Gi Longhorn, 7-day retention
  - Grafana: 5Gi Longhorn (dashboards in ConfigMaps, not DB)
Alertmanager: route critical → PagerDuty; warning → Slack #alerts
Ingress: observability tools exposed via NGINX Ingress with mTLS (internal only)
```

**RU:**
```
/observability-stack-setup

Кластер: prod-cluster-eu (bare-metal K8s 1.31, Cilium)
Хранилище: Longhorn (блочное хранилище доступно)
Стек для деплоя (через Helm + ArgoCD):
  - kube-prometheus-stack (Prometheus + Alertmanager + Grafana + node-exporter + kube-state-metrics)
  - Loki (single binary на старте; distributed когда логи > 50GB/день)
  - Promtail DaemonSet (сбор логов со всех подов)
  - Tempo (distributed tracing, single binary)
  - OpenTelemetry Collector (DaemonSet, принимает OTLP)
  - Datasources в Grafana: Prometheus + Loki + Tempo (авто-настройка)
Persistence:
  - Prometheus: 50Gi Longhorn, хранение 15 дней
  - Loki: 100Gi Longhorn, хранение 30 дней
  - Tempo: 50Gi Longhorn, хранение 7 дней
  - Grafana: 5Gi Longhorn (дашборды в ConfigMaps, не в БД)
Alertmanager: critical → PagerDuty; warning → Slack #alerts
Ingress: инструменты observability через NGINX Ingress с mTLS (только внутренний доступ)
```

---

## Example 2 — Migrate from ELK to Loki (cost reduction)

**EN:**
```
/observability-stack-setup

Task: migrate log aggregation from Elasticsearch + Kibana to Grafana Loki
Current: ELK stack consuming 200Gi storage, 8 CPU, 32Gi memory (3 ES nodes)
Target: Loki in single binary mode (~2 CPU, 4Gi memory, 100Gi storage)
Migration constraints:
  - Zero log gap during migration (dual-write period)
  - Existing Kibana dashboards must be recreated in Grafana (or translated)
  - Historical logs from ES: export last 7 days to Loki (beyond that, discard)
  - Application log format: already JSON structured
Migration plan:
  1. Deploy Loki + Grafana alongside existing ELK
  2. Configure Fluent Bit to ship to both (dual-write, 1 week)
  3. Recreate critical Kibana dashboards in Grafana LogQL
  4. Decommission ELK after 1 week parallel operation
  5. Reclaim storage and compute
```

**RU:**
```
/observability-stack-setup

Задача: миграция агрегации логов с Elasticsearch + Kibana на Grafana Loki
Текущее: ELK стек потребляет 200Gi хранилища, 8 CPU, 32Gi памяти (3 ноды ES)
Цель: Loki в single binary режиме (~2 CPU, 4Gi памяти, 100Gi хранилища)
Ограничения миграции:
  - Нулевой пробел в логах во время миграции (период двойной записи)
  - Существующие дашборды Kibana должны быть воссозданы в Grafana (или транслированы)
  - Исторические логи из ES: экспорт последних 7 дней в Loki (далее — удалить)
  - Формат логов приложений: уже JSON структурированный
План миграции:
  1. Развернуть Loki + Grafana рядом с существующим ELK
  2. Настроить Fluent Bit для отправки в оба (двойная запись, 1 неделя)
  3. Воссоздать критичные дашборды Kibana в Grafana LogQL
  4. Вывести из эксплуатации ELK после 1 недели параллельной работы
  5. Вернуть хранилище и вычислительные ресурсы
```
