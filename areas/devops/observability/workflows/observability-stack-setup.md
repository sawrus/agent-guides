---
name: observability-stack-setup
type: workflow
trigger: /observability-stack-setup
description: Deploy the full observability stack (Prometheus + Loki + Tempo + Grafana) to a Kubernetes cluster from scratch.
inputs:
  - cluster_name
  - storage_class
  - retention_days_metrics
  - retention_days_logs
outputs:
  - running_observability_stack
  - grafana_url
  - setup_report
roles:
  - devops-engineer
execution:
  initiator: developer
related-rules:
  - golden-signals.md
  - alerting-standards.md
  - data-retention.md
uses-skills:
  - prometheus-alertmanager
  - grafana-dashboards
  - log-aggregation
  - distributed-tracing
  - slo-implementation
quality-gates:
  - all components healthy (Prometheus targets UP)
  - sample alert fires and reaches Alertmanager
  - Grafana shows data from all three pillars (metrics/logs/traces)
---

## Steps

### 1. Namespace & Prerequisites — `@devops-engineer`
```bash
kubectl create namespace monitoring
kubectl create namespace logging
kubectl create namespace tracing

# Add Helm repos
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana              https://grafana.github.io/helm-charts
helm repo update
```

### 2. kube-prometheus-stack (Prometheus + Grafana + Alertmanager) — `@devops-engineer`
```bash
helm upgrade --install kube-prometheus-stack \
  prometheus-community/kube-prometheus-stack \
  -n monitoring \
  -f infra/observability/prometheus-values.yaml \
  --create-namespace

# prometheus-values.yaml (key sections)
# prometheus:
#   prometheusSpec:
#     retention: 15d
#     storageSpec:
#       volumeClaimTemplate:
#         spec:
#           storageClassName: longhorn
#           resources: { requests: { storage: 50Gi } }
# alertmanager:
#   config: <alertmanager routing config>
# grafana:
#   adminPassword: <from Vault>
#   persistence: { enabled: true, storageClassName: longhorn, size: 10Gi }
```
- Verify: `kubectl get pods -n monitoring` — all Running
- Check Prometheus targets: `kubectl port-forward svc/kube-prometheus-stack-prometheus 9090:9090 -n monitoring`

### 3. Loki + Promtail (Logs) — `@devops-engineer`
```bash
helm upgrade --install loki grafana/loki-stack \
  -n logging \
  -f infra/observability/loki-values.yaml \
  --create-namespace

# loki-values.yaml key settings:
# loki.config.limits_config.retention_period: 720h  (30d)
# promtail.config.clients[0].url: http://loki.logging:3100/loki/api/v1/push
```
- Add Loki datasource in Grafana: `http://loki.logging:3100`
- Verify: `{job="loki"}` returns logs in Grafana Explore

### 4. Tempo (Traces) — `@devops-engineer`
```bash
helm upgrade --install tempo grafana/tempo \
  -n tracing \
  -f infra/observability/tempo-values.yaml \
  --create-namespace

# tempo-values.yaml key settings:
# tempo.retention: 168h  (7d)
# persistence.enabled: true
# tempo.receivers.otlp.protocols.grpc.endpoint: 0.0.0.0:4317
```
- Add Tempo datasource in Grafana: `http://tempo.tracing:3100`
- Configure trace-to-log correlation: set Loki derived field `traceID` → Tempo URL

### 5. OpenTelemetry Collector (DaemonSet) — `@devops-engineer`
```bash
helm upgrade --install otel-collector open-telemetry/opentelemetry-collector \
  -n monitoring \
  -f infra/observability/otel-collector-values.yaml
```
- Accepts OTLP from apps (port 4317 gRPC, 4318 HTTP)
- Forwards to Tempo

### 6. Validate Stack — `@devops-engineer`
```bash
# Test Prometheus query
kubectl exec -n monitoring deploy/prometheus -- \
  wget -qO- 'http://localhost:9090/api/v1/query?query=up' | jq '.data.result | length'

# Test alert routing: create test alert
kubectl apply -f - << 'YAML'
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: test-alert
  namespace: monitoring
spec:
  groups:
    - name: test
      rules:
        - alert: TestAlert
          expr: vector(1)   # always fires
          labels: { severity: warning }
          annotations: { summary: "Test alert for stack validation" }
YAML
# Check Alertmanager received it: kubectl port-forward svc/alertmanager 9093:9093 -n monitoring

# Test logs visible
kubectl port-forward svc/grafana 3000:80 -n monitoring
# Open Grafana → Explore → Loki → {job="monitoring"} → should show logs
```

### 7. Import Dashboards — `@devops-engineer`
```bash
# Apply standard dashboard ConfigMaps (GitOps)
kubectl apply -f infra/observability/dashboards/ -n monitoring

# Or import via Grafana API
for dashboard in infra/observability/dashboards/*.json; do
  curl -X POST http://admin:${GRAFANA_PASS}@localhost:3000/api/dashboards/import \
    -H 'Content-Type: application/json' \
    -d "{\"dashboard\": $(cat $dashboard), \"overwrite\": true}"
done
```

## Exit
All 4 components healthy + test alert fired + dashboards showing data = stack deployed.
