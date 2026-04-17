---
name: distributed-tracing
type: skill
description: "Implement distributed tracing with OpenTelemetry, Tempo/Jaeger — instrumentation, sampling, and trace-to-log correlation. Use when the user asks about distributed tracing, OpenTelemetry setup, span instrumentation, trace propagation, or connecting traces to logs and metrics."
related-rules:
  - golden-signals.md
  - data-retention.md
allowed-tools: Read, Write, Edit
---

# Skill: Distributed Tracing

> **Expertise:** OpenTelemetry SDK, auto-instrumentation, Tempo/Jaeger, trace-log correlation, sampling strategies.

## When to load

When adding tracing to a service, debugging slow distributed transactions, or setting up trace → log → metric correlation.

## End-to-End Setup Workflow

1. **Deploy collector** — configure and deploy the OTel Collector as a DaemonSet (see config below)
2. **Instrument service** — add SDK initialization and auto-instrumentation for your framework (Python/Go examples below)
3. **Verify traces** — confirm traces appear in Tempo/Jaeger: `curl -s http://tempo:3200/api/search?q={}&limit=5`
4. **Add log correlation** — inject `trace_id` and `span_id` into log lines for Loki/Grafana linkage
5. **Validate linkage** — click a trace in Grafana → Explore → verify it links to the corresponding log entries
6. **Tune sampling** — apply tail-based sampling policies for errors and slow traces (see strategy table)

## OpenTelemetry Collector (K8s DaemonSet)

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc: { endpoint: "0.0.0.0:4317" }
      http: { endpoint: "0.0.0.0:4318" }

processors:
  batch:
    timeout: 1s
    send_batch_size: 1000
  memory_limiter:
    check_interval: 1s
    limit_mib: 400

  # Tail-based sampling — sample 100% of error/slow traces
  tail_sampling:
    decision_wait: 10s
    policies:
      - name: errors-policy
        type: status_code
        status_code: { status_codes: [ERROR] }
      - name: slow-traces
        type: latency
        latency: { threshold_ms: 500 }
      - name: probabilistic-10pct
        type: probabilistic
        probabilistic: { sampling_percentage: 10 }

exporters:
  otlp/tempo:
    endpoint: tempo:4317
    tls: { insecure: true }

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, tail_sampling, batch]
      exporters: [otlp/tempo]
```

## Python Auto-Instrumentation (FastAPI)

```python
# main.py — add before app creation
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

provider = TracerProvider()
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="otel-collector:4317"))
)
trace.set_tracer_provider(provider)

# Auto-instrument frameworks
FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()  # outgoing HTTP calls
SQLAlchemyInstrumentor().instrument()   # DB queries
```

## Go Auto-Instrumentation

```go
// tracing/setup.go
func InitTracer(serviceName string) func() {
    exporter, _ := otlptracegrpc.New(ctx,
        otlptracegrpc.WithEndpoint("otel-collector:4317"),
        otlptracegrpc.WithInsecure(),
    )
    tp := tracesdk.NewTracerProvider(
        tracesdk.WithBatcher(exporter),
        tracesdk.WithResource(resource.NewWithAttributes(
            semconv.SchemaURL,
            semconv.ServiceNameKey.String(serviceName),
        )),
    )
    otel.SetTracerProvider(tp)
    otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
        propagation.TraceContext{},
        propagation.Baggage{},
    ))
    return func() { tp.Shutdown(ctx) }
}
```

## Trace-to-Log Correlation

```python
# Inject trace_id and span_id into every log line
import logging
from opentelemetry import trace

class TraceContextFilter(logging.Filter):
    def filter(self, record):
        span = trace.get_current_span()
        ctx = span.get_span_context()
        record.trace_id = format(ctx.trace_id, '032x') if ctx.is_valid else ''
        record.span_id  = format(ctx.span_id,  '016x') if ctx.is_valid else ''
        return True

# Log format: {"message": "...", "trace_id": "abc123", "span_id": "def456"}
# Loki/Grafana links trace_id → Tempo automatically
```

## K8s Pod Annotation for Auto-Instrumentation (Operator)

```yaml
# Using OpenTelemetry Operator — zero code change instrumentation
metadata:
  annotations:
    instrumentation.opentelemetry.io/inject-python: "true"
    # For Java: inject-java, Go: inject-go
```

## Sampling Strategy

| Scenario | Strategy | Rate |
|:---|:---|:---|
| Normal traffic | Probabilistic (head-based) | 10% |
| Errors | Always sample | 100% |
| Latency > p99 | Tail-based | 100% |
| Debug/investigation | Force-sample via baggage | 100% |
