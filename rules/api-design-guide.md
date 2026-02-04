---
trigger: model_decision
glob: api-design-guide
description: API contracts must be explicit, validated, and versioned
---

# API Design Rule

**Rules:**

- Use Pydantic for request/response validation; enforce strict types, no raw dicts.
- Implement `/liveness` and `/readiness` for K8s probes.
- Implement `/metrics` for FastAPI using PrometheusMiddleware.
- Version APIs in path or headers (v1, v2…).
- Sanitize input; output must be explicit.
- Document all endpoints with OpenAPI/Swagger.
- No side effects in GET requests.
- Responses must include status codes and error details.

**Violations:**

- API schemas are implicit.
- Validation is ad-hoc.
- Endpoints mutate state unexpectedly.
