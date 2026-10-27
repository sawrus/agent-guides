---
name: api-design
description: "Procedure to add or change an HTTP (OpenAPI) or gRPC (protobuf) API contract: edit the spec first, check breaking changes with oasdiff or buf, version and deprecate, and add contract tests. Use when you add or change an endpoint, request or response schema, or a proto service."
---

# API contract: add or change

## 1. Find the contract

1. Look for the spec: `openapi.yaml`, `api/*.yaml`, `docs/api/`, `*.proto` under `proto/` or `api/`.
2. If the code generates the spec (FastAPI, springdoc, swaggo), find the command that exports it and use the
   exported file in step 4.
3. If no spec exists, write down the current request and response of the endpoint from the code and its tests.
4. Find the consumers: other services, frontends, published SDKs. Ask the user if they are not known.

## 2. Edit the contract first

1. Change the spec before the code. Keep the change to the endpoint or message the task names.
2. HTTP: one resource per path, plural nouns (`/orders/{orderId}`), standard methods and status codes, one
   error schema for all endpoints (for example RFC 9457 `application/problem+json`).
3. List endpoints take `limit` and a cursor (`page_token` / `next_page_token`) and return a bounded page.
4. A create endpoint that clients may retry accepts an `Idempotency-Key` header.
5. gRPC: add fields with new field numbers. Never reuse or renumber a field; `reserved` removed numbers and names.

## 3. Classify the change

Additive (safe):
- new endpoint, new optional request field, new response field, new enum value that clients ignore.

Breaking:
- removed or renamed field or endpoint, new required request field, changed type or format, changed status code,
  stricter validation, changed field number or name in proto.

## 4. Check breaking changes with a tool

```bash
git show origin/main:openapi.yaml > /tmp/base.yaml
oasdiff breaking /tmp/base.yaml openapi.yaml --fail-on ERR
buf breaking --against '.git#branch=main'
```

If the tool reports a breaking change, do one of these:

1. Make it additive: keep the old field, add the new one, and map both in the code.
2. Add a new version (`/v2/...` path or a new proto package `v2`) and keep the old version running.
3. If the user accepts the break, mark it as breaking in the changelog and the merge request, and name the
   consumers that must change.

## 5. Deprecate

1. Mark the old field or endpoint `deprecated: true` (OpenAPI) or `[deprecated = true]` (proto).
2. HTTP: return `Deprecation` and `Sunset` headers on deprecated endpoints.
3. Write the removal date in the API docs page. Remove only after consumers stop calling it (check access logs
   or metrics).

## 6. Implement and test

1. Generate server stubs or types from the spec if the project does so (`buf generate`, `openapi-generator`).
2. Add tests for the success response, each documented error status, and validation of each new field.
3. Add a contract test that checks responses against the spec (`schemathesis run openapi.yaml --url <local>`,
   Pact, or a schema assertion in the API tests).
4. Update the API docs page and the changelog in the same change.
