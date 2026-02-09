---
name: testing-ci-pipeline
type: workflow
description: Run CI & Testing pipeline. Abstract workflow usable for both Backend and Frontend.
inputs:
  - project_type (backend|frontend)
  - test_scope (unit|e2e|all)
outputs:
  - test_report
related-rules:
  - testing-ci-guide.md
  - code-quality-guide.md
uses-skills:
  - blackbox-testing
---

# Testing & CI Workflow

**Goal:** Verify code quality and functionality.

## Steps

1.  **Code Quality Check**
    - Action: Run Linters & Formatters.
    - Expectation: No errors.
    - _Note:_ Uses project-specific tools (e.g., `ruff` for Python, `eslint` for JS).

2.  **Unit Tests**
    - Action: Run Unit Tests.
    - Expectation: Pass with required coverage.

3.  **Build / Prepare (If applicable)**
    - Action: Build artifacts or Docker containers.
    - Expectation: Successful build.

4.  **E2E / Integration Tests**
    - Action: Run Blackbox/E2E tests.
    - Condition: If `test_scope` includes 'e2e' or 'all'.
    - Expectation: All scenarios pass.

## Failure Policy

- If any step fails, the pipeline halts.
- Fix violations before proceeding.
