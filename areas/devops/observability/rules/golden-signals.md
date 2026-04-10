# Rule: Golden Signals & SLO-First Observability Baseline

**Priority**: P1 — Services without measurable user-impact SLIs and enforceable SLO alerts cannot be promoted to production.

## Required Coverage

1. **Golden signals are mandatory**: latency, traffic, errors, saturation.
2. **User-journey SLIs are mandatory** for critical flows (e.g., checkout success, login success, payment confirmation latency).
3. **Instrumentation is vendor-neutral**: do not hardcode stack-specific ports/endpoints in policy; enforce metric contract and discoverability.

## Signal Baseline

| Signal | Minimum metric coverage | Alerting baseline |
|:---|:---|:---|
| Latency | p50/p95/p99 by endpoint/operation | p99 SLO burn alert |
| Traffic | request rate + success volume | anomaly vs rolling baseline |
| Errors | error rate by class (4xx/5xx/domain) | user-impacting error budget burn |
| Saturation | CPU, memory, queue/concurrency, DB saturation | sustained saturation with user impact |

## SLO and Alerting Requirements

4. Define at least one availability and one latency SLO per critical service.
5. Use multi-window multi-burn-rate alerting (fast + slow burn).
6. Link alert severity to error-budget policy actions.
7. Every alert must include runbook URL and primary owner.

## Cardinality and Cost Governance

8. Define metric label cardinality budget per service.
9. For high-cardinality telemetry, apply sampling, aggregation, or drop policy with documented rationale.
10. Retention tiers must be explicit and mapped to compliance + incident forensics needs.

## Trace and Log Correlation

11. Propagate trace context across service boundaries.
12. Ensure logs, metrics, and traces can be correlated via request/trace IDs.
13. Sensitive data must be redacted before ingestion.
