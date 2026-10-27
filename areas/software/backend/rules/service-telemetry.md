---
description: Logs, metrics, and trace context emitted by backend service code.
paths:
  - "**/*.py"
  - "**/*.go"
  - "**/*.java"
  - "**/*.kt"
---

# Service telemetry

- Write logs as structured JSON with `timestamp`, `level`, `service`, `message`, and `trace_id`.
- Use the project logger (`structlog`/`logging`, `slog`/`zap`, SLF4J); never use `print`, `fmt.Println`, or `System.out` in service code.
- Log an error once, where it is handled, with the stack trace and the ids needed to find the request.
- Propagate W3C `traceparent` on every inbound and outbound HTTP, gRPC, and broker call.
- Add the request id to every log line of a request (contextvars, MDC, `context.Context`).
- Expose request rate, error count, and latency histogram per endpoint (`http_server_request_duration_seconds`).
- Expose a counter or histogram for every queue consumer and background job (processed, failed, duration).
- Keep metric label values bounded: never use user id, email, or raw URL path as a label.
- Do not log request or response bodies that contain personal data or credentials.
