---
description: Layering, service boundaries, remote calls, and background jobs in Python, Go, and Java backend services.
paths:
  - "**/*.py"
  - "**/*.go"
  - "**/*.java"
  - "**/*.kt"
---

# Service architecture

- Keep three layers: handlers (HTTP, gRPC, CLI, consumer) call services; services call repositories and clients.
- Do not import a repository, ORM session, or database driver in a handler module.
- Do not import web framework types (`Request`, `HttpServletRequest`, `gin.Context`) in a service or repository.
- Return domain types or DTOs from a repository; never return ORM entities to a handler.
- Keep business rules out of handlers; a handler only parses input, calls one service method, and maps the result.
- Define the transaction boundary in the service layer, not in a handler or repository.
- Never share a database schema between two services; read another service's data through its API or events.
- Set an explicit timeout on every outbound HTTP, gRPC, database, and broker call; no call uses an unbounded default.
- Retry only idempotent remote calls, with capped exponential backoff and jitter; limit retries to 3 by default.
- Catch specific exception types; never catch the base `Exception`/`Throwable` or discard an `error` value in Go.
- Map internal errors to one error response type at the handler; do not leak stack traces in a response body.
- Make every background job and message consumer idempotent: use a deduplication key or an upsert.
- Set a concurrency limit and a dead-letter queue for every consumer and job queue.
- Do not run blocking I/O or CPU-heavy work on an async event loop (`asyncio`, Netty, Reactor); offload it.
- Do not perform external I/O (HTTP, broker publish) inside an open database transaction; use an outbox table.
- Add new dependencies between modules only in the direction handler → service → repository; no import cycles.
