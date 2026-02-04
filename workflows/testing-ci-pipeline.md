---
trigger: always_on
glob: testing-ci-guide
description: Run CI & Testing pipeline after every new AI task
---

# Testing & CI Workflow

**Steps (invokes Rule)**:

1. **Migrate Database**
    - command: `make migrate`
    - expect: no errors
2. **Format & Lint**
    - command: `make format lint`
    - expect: all checks passed
3. **Unit Tests**
    - command: `make test-cov`
    - expect: coverage ≥70%
4. **Start Services**
    - command: `make docker-up`
    - expect: no errors in logs
5. **E2E Test**
    - command: `make e2e-test`
    - expect: all scenarios passed
6. **SVT Test**
    - command: `make svt-test`
    - expect: all load test scenarios passed

**Rules Applied**:

- testing-ci-guide.md

**Violations**:

- Any stage fails → report as violation
