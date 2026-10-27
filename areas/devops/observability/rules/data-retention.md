---
description: Retention, sampling, and cardinality limits for metrics, logs, and traces in the observability stack.
paths:
  - "**/prometheus*.yml"
  - "**/prometheus*.yaml"
  - "**/loki*.yaml"
  - "**/tempo*.yaml"
  - "**/otel*.yaml"
  - "**/otel*.yml"
  - "**/values-*observability*.yaml"
---

# Observability data retention

- Keep raw Prometheus metrics for 15 days and downsampled metrics in long-term storage (Thanos, Mimir, VictoriaMetrics) for 1 year.
- Keep logs hot for 30 days and in cold storage for 90 days, then delete them.
- Keep traces for 7 days and do not archive them.
- Never use `user_id`, `session_id`, `request_id`, or `trace_id` as a metric label.
- Limit each service to the series budget set in its scrape config with `sample_limit`.
- Drop unused high-cardinality series with `metric_relabel_configs` before ingestion.
- Sample `DEBUG` logs at 1 % in production and keep all `INFO`, `WARN`, and `ERROR` logs.
- Sample 10 % of traces at the head and keep every error trace and every trace slower than p99 with tail sampling.
- Use recording rules for queries that dashboards run on raw high-volume metrics.
- Redact secrets and personal data in the collector (`attributes` or `transform` processor) before export.
