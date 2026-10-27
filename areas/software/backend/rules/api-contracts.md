---
description: HTTP and gRPC API contracts of backend services — schemas, versions, errors, and health endpoints.
paths:
  - "**/openapi*.yaml"
  - "**/openapi*.json"
  - "**/*.proto"
  - "**/api/**"
  - "**/routes/**"
  - "**/handlers/**"
  - "**/controllers/**"
---

# API contracts

- Keep the contract in the repository (`openapi.yaml` or `*.proto`) and update it in the same change as the handler.
- Declare a typed request and response schema for every endpoint; no untyped `dict`, `map[string]any`, or `Object` bodies.
- Version public APIs in the path (`/v1/`) or package (`package orders.v1`); never break a released version.
- Treat as breaking: removing a field or endpoint, renaming, changing a type, making an optional field required.
- Run a breaking-change check (`oasdiff breaking`, `buf breaking`) in CI against the main branch contract.
- Mark a field or endpoint `deprecated` at least one release before you remove it.
- Do not change state in `GET`, `HEAD`, or `OPTIONS` handlers.
- Return one error schema for all errors (for example RFC 9457 `application/problem+json`) with a stable `code` field.
- Return `400` for invalid input, `401` without credentials, `403` without permission, `404` for unknown ids, `409` for conflicts.
- Require an `Idempotency-Key` header or a natural key for `POST` endpoints that create payments, orders, or messages.
- Use cursor pagination with a `limit` cap for list endpoints; never return an unbounded list.
- Expose `/livez` (or `/healthz`) and `/readyz`; the readiness check covers the database and required brokers.
- Expose metrics on `/metrics` or through OpenTelemetry for every service.
