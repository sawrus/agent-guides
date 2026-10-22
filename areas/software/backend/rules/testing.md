---
trigger: manual
description: backend test pyramid, mock boundaries, and contract tests
---
# Rule: Backend Testing Pyramid

**Priority**: P1 — Missing critical-path coverage fails review.

## Testing layers

1. **Unit tests**
   - Isolated domain/application logic tests.
   - External dependencies must be mocked.

2. **Integration tests**
   - Validate real integration with databases/message systems.
   - Use realistic infrastructure (for example, Testcontainers).

3. **E2E/API tests**
   - Verify critical user and system flows through service interfaces.

4. **SVT/chaos (when relevant)**
   - Validate resilience under partial failure and degraded conditions.
