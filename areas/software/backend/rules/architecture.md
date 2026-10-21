---
trigger: manual
description: layering, module boundaries, and dependency direction for backend services
---
# Rule: Backend Architecture (Microservices & Zero Trust)

**Priority**: P0 — Architectural violations block deployment.

## Core principles

1. **Microservices First**
   - Each service owns one bounded context.
   - Shared databases across microservices are forbidden (except read-only analytical replicas).
   - Services must support independent deployment.

2. **Zero Trust Architecture**
   - No request is trusted by default, including internal traffic.
   - Inter-service communication must use mTLS or signed service tokens.
   - Enforce least privilege for every service identity.

3. **API and communication strategy**
   - Use synchronous calls (REST/gRPC) only when immediate responses are required.
   - Prefer asynchronous event-driven communication (Kafka/NATS/RabbitMQ) for service-to-service flows.
   - Use circuit breakers and retries with exponential backoff for external dependencies.
