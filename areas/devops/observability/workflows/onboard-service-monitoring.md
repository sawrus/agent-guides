---
name: onboard-service-monitoring
type: workflow
trigger: /onboard-service-monitoring
description: Add full observability (metrics, logs, traces, alerts, dashboard) to an existing service.
inputs:
  - service_name
  - namespace
  - language/framework
outputs:
  - running_metrics_scrape
  - grafana_dashboard
  - alert_rules_deployed
roles:
  - devops-engineer
  - developer
execution:
  initiator: developer
related-rules:
  - golden-signals.md
  - alerting-standards.md
uses-skills:
  - prometheus-alertmanager
  - grafana-dashboards
  - distributed-tracing
  - log-aggregation
quality-gates:
  - all four golden signals visible in Prometheus
  - at least one critical alert deployed with runbook
  - logs visible in Loki with trace_id field
---

## Steps

### 1. Metrics Instrumentation — `@developer`
- Add Prometheus client library to service
- Expose standard HTTP metrics (requests_total, duration histogram, active_requests)
- Expose `/metrics` endpoint on port 9090 (or sidecar annotation)
- **Done when:** `curl http://<pod-ip>:9090/metrics` returns Prometheus format

### 2. ServiceMonitor — `@devops-engineer`
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: ${SERVICE}
  namespace: ${NAMESPACE}
spec:
  selector:
    matchLabels: { app: ${SERVICE} }
  endpoints:
    - port: metrics
      interval: 15s
      path: /metrics
```
- **Done when:** Prometheus targets page shows service as UP

### 3. Tracing Instrumentation — `@developer`
- Add OpenTelemetry SDK (or use K8s operator auto-injection)
- Configure OTLP exporter → otel-collector:4317
- Verify trace_id appears in application logs
- **Done when:** traces visible in Tempo; trace_id in logs

### 4. Log Labels — `@devops-engineer`
- Verify Promtail/Fluent Bit picks up pod logs
- Confirm JSON parsing works: `{namespace="${NS}", app="${SERVICE}"} | json`
- Add log-based alert if service emits structured error logs
- **Done when:** logs searchable in Loki with level + trace_id fields

### 5. Alert Rules — `@devops-engineer`
- Create `PrometheusRule` with golden signal alerts (HighErrorRate, HighP99Latency, PodMemoryPressure)
- Write runbook for each alert in `docs/runbooks/`
- Test alert firing: temporarily lower threshold, verify Alertmanager receives it
- **Done when:** all alerts show in Prometheus rules page; test fire works

### 6. Grafana Dashboard — `@devops-engineer`
- Import standard service overview dashboard template
- Customize: add service-specific panels (queue depth, custom business metrics)
- Link trace panel (Tempo datasource) to request duration panel
- **Done when:** dashboard saved in `infra/dashboards/`; Grafana shows live data

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /onboard-service-monitoring"])
  role_1["developer"]
  role_2["devops-engineer"]
  step_1["1. Metrics Instrumentation"]
  step_2["2. ServiceMonitor"]
  step_3["3. Tracing Instrumentation"]
  step_4["4. Log Labels"]
  step_5["5. Alert Rules"]
  step_6["6. Grafana Dashboard"]
  exit(["Golden signals in Prometheus + logs in Loki + traces in Tempo + alerts depl..."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> step_6
  step_6 --> exit
  role_1 -. owns .-> step_1
  role_2 -. owns .-> step_2
  role_1 -. owns .-> step_3
  role_2 -. owns .-> step_4
  role_2 -. owns .-> step_5
  role_2 -. owns .-> step_6
```
<!-- agent-diagram:end -->

## Exit
Golden signals in Prometheus + logs in Loki + traces in Tempo + alerts deployed + dashboard live = service monitored.
