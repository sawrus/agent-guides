---
name: feature-implementation-flow
type: workflow
description: Focused workflow for implementing a single feature in an existing backend service.
inputs:
  - feature_request
  - existing_codebase
outputs:
  - implemented_feature
  - passing_tests
related-rules:
  - backend-architecture-rule.md
  - code-quality-guide.md
  - testing-ci-guide.md
uses-skills:
  - backend-developer
---

## 🎯 Workflow Goal

Implement a specific feature request into an existing service, adhering to layered architecture.

## 🛠️ Phase 1 — Analysis & Models

1.  **Understand Requirement:** Read the feature request and identify impacted domain entities.
2.  **Update Models:**
    - Modify `src/models/` (SQLAlchemy) if schema changes are needed.
    - Create usage migration (Alembic).
3.  **Update Schemas:**
    - Define Pydantic models in `src/schemas/` for Input/Output.

## 💻 Phase 2 — Implementation (Inner to Outer)

1.  **Repository Layer:**
    - Implement data access methods in `src/repositories/`.
    - Ensure IO-bound operations are async.
2.  **Service Layer:**
    - Implement business logic in `src/services/`.
    - Inject Repository dependencies.
    - Handle exceptions and convert to business errors.
3.  **API Layer:**
    - Add/Update endpoints in `src/api/`.
    - Connect Service methods to Endpoints.

## 🧪 Phase 3 — Verification

1.  **Unit Tests:**
    - Test Service logic (mocking Repositories).
    - Test Repository logic (using test DB or mocks).
2.  **Integration Tests:**
    - Test API endpoints (e2e) using a test client.
3.  **Quality Check:**
    - Verify no linting errors.
    - Verify strict typing.
