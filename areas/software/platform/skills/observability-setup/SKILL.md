---
name: observability-setup
description: "Sets up service observability with mandatory golden signals, Prometheus alert rules, and a structured logging contract; use when setting up monitoring for a new service, configuring alerts, or debugging production issues."
---

# Skill: Observability Setup

## When to load

When setting up monitoring for a new service, configuring alerts, debugging production issues.

## Golden Signals (Mandatory)

Every service must expose:
1. **Latency**: p50, p95, p99 response times
2. **Traffic**: requests per second
3. **Errors**: 4xx/5xx rate
4. **Saturation**: CPU %, memory %, queue depth

## Prometheus Alert Rules

```yaml
groups:
  - name: api-alerts
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m]))
          / sum(rate(http_requests_total[5m])) > 0.01
        for: 2m
        labels: { severity: critical }
        annotations:
          summary: "Error rate > 1% for 2 minutes"
          runbook: "https://runbooks.internal/high-error-rate"

      - alert: HighLatency
        expr: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels: { severity: warning }
```

## Structured Logging Contract

```json
{
  "timestamp": "2026-02-16T10:30:00Z",
  "level": "ERROR",
  "service": "payments-api",
  "trace_id": "abc123",
  "message": "Payment processing failed",
  "error": { "type": "PaymentGatewayError", "code": "CARD_DECLINED" },
  "duration_ms": 1240
}
```
