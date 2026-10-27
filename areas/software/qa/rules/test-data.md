---
description: Test data sources, isolation, and fake value conventions for automated tests.
paths:
  - "**/tests/**"
  - "**/fixtures/**"
  - "**/factories/**"
---

# Test data

- Never copy production data into tests; use synthetic data from factories.
- Create the data each test needs inside the test, and delete it in teardown or roll back the transaction.
- Do not share mutable state between tests; each test must pass when run alone and in random order.
- Use factories (`factory_boy`, `@faker-js/faker`) instead of raw SQL fixture files.
- Use `example.com` addresses and obviously fake phone numbers in test data.
- Set a fixed seed for fake data generators so a failing test reproduces.
