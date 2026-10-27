---
description: Handling of flaky tests, covering quarantine, root cause, and the fix deadline.
paths:
  - "**/tests/**"
  - "**/test/**"
  - "**/*_test.*"
  - "**/*.spec.*"
  - "**/*.test.*"
---

# Flaky tests

- Quarantine a test that fails in more than 2% of runs on the main branch, and open a tracking issue for it.
- Fix or delete a quarantined test within 5 business days.
- Name the cause in the fix commit: race condition, shared state, external service, or time dependency.
- Do not add `sleep()` or a fixed wait to fix a flaky test; wait on an explicit condition instead.
- Use an injected or frozen clock in tests instead of `Date.now()` or `time.time()`.
- Use a fake or a local container instead of external services in unit and integration tests.
