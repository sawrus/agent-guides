---
description: Unit, integration, and API test requirements for backend services in Python, Go, and Java.
paths:
  - "**/tests/**"
  - "**/test/**"
  - "**/*_test.go"
  - "**/test_*.py"
  - "**/*Test.java"
  - "**/*Test.kt"
---

# Backend testing

- Add a unit test for every new or changed public function of the service layer, with one success and one failure case.
- Mock only external boundaries (HTTP clients, brokers, clock); do not mock the code under test or the ORM.
- Run integration tests against the real database and broker engine (Testcontainers or a compose service), not SQLite or in-memory fakes.
- Add an API test for every new endpoint that checks the status code, response schema, and one error response.
- Add a regression test that fails before the fix for every bug fix.
- Keep tests independent: each test creates its own data and does not depend on test order.
- Do not call real third-party services or production endpoints from tests; use a stub server.
- Use fixed seeds and an injected clock; no test reads the wall clock or random values directly.
- Keep the coverage threshold in the test config (`--cov-fail-under`, JaCoCo rule, `go test -cover` gate); do not lower it in a change.
- Do not delete or skip a failing test to make the build pass; mark a quarantined test with a ticket id.
- Name tests after behaviour (`test_rejects_expired_token`), not after the method (`test_method1`).
