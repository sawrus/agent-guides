---
description: Golden-signal metrics, SLO coverage, and correlation that every production service exposes and dashboards show.
paths:
  - "**/dashboards/**"
  - "**/grafana/**"
  - "**/servicemonitor*.yaml"
  - "**/podmonitor*.yaml"
  - "**/slo*.yaml"
  - "**/sloth/**"
---

# Golden signals

- Expose request rate, error rate, and latency histogram metrics for every endpoint or operation (for example `http_server_request_duration_seconds`).
- Expose saturation metrics: CPU, memory, connection pool use, and queue depth or worker concurrency.
- Label error metrics by class (`4xx`, `5xx`, or domain error code) and keep the label set bounded.
- Use histograms, not summaries, for latency so p50, p95, and p99 can be aggregated across pods.
- Add a `ServiceMonitor` or `PodMonitor` (or a scrape config) for every production service.
- Define at least one availability SLO and one latency SLO for every critical service and its main user journeys.
- Put one dashboard per service in the repository with panels for rate, errors, p99 latency, saturation, and SLO burn.
- Store dashboards as JSON or code (Grafonnet, Terraform) in the repository; do not edit production dashboards only in the UI.
- Propagate W3C `traceparent` across every service call and message.
- Write the `trace_id` into every log line so logs, metrics exemplars, and traces correlate.
