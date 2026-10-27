---
description: Test suite shape, coverage ratchet, and test naming for automated test suites.
paths:
  - "**/tests/**"
  - "**/test/**"
  - "**/*_test.*"
  - "**/*.spec.*"
  - "**/*.test.*"
---

# Test strategy

- Keep roughly 20 unit tests and 5 integration tests for every end-to-end test.
- Add the tests for a feature or bug fix in the same change as the code.
- Add a regression test to every hotfix before the fix counts as complete.
- Keep coverage at or above the target branch value; do not lower the coverage threshold in config.
- Name a test as `<unit> <scenario> <expected result>`, for example `checkout with expired card shows error`.
- Do not name tests with numbers only, such as `test_checkout_2`.
