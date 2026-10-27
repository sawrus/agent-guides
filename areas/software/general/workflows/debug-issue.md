---
name: debug-issue
type: workflow
trigger: /debug-issue
description: Find the root cause of a bug, fix it with a regression test, and record the cause.
inputs:
  - bug_report
  - logs_or_stack_trace
outputs:
  - fix
  - regression_test
  - docs_page
selection:
  general: false
  use-when: "The request reports wrong behaviour, an error, a crash, a failing test or a regression in application code and asks to find the cause and fix it."
  avoid-when: "A live production incident that needs mitigation first, or a pod or cluster failure in Kubernetes."
uses-skills: []
related-rules:
  - code-style-guide.md
  - docs-layout.md
checks:
  - make lint
  - make test
---

# Debug an issue

Example request: `/debug-issue "POST /orders returns 500 when the cart holds a discounted item"`

## Steps

### 1. Reproduce

- **Do:** turn the report into one command that shows the failure: a failing test, a `curl` call, or a script.
  Collect the exact error, stack trace, version, and input. Read logs only from the environment named in the
  report; ask the user first before you query a production system.
- **Done when:** the failure reproduces with one command, or you report the missing data that blocks it.

### 2. Locate the cause

- **Do:** narrow the fault with evidence: bisect commits (`git bisect run <cmd>`), add temporary logging, or
  step through the failing path. Write down each hypothesis and the fact that confirms or rejects it.
- **Done when:** you can name the line or condition that causes the failure and explain why it was possible.

### 3. Write the regression test

- **Do:** add a test at the lowest level that exercises the cause. Run it before the fix.
- **Done when:** the new test fails on the current code for the reported reason.

### 4. Fix

- **Do:** change the code at the cause, not at the symptom. Remove the temporary logging. Search for the same
  pattern elsewhere (`grep -rn`) and list other hits instead of fixing them silently.
- **Done when:** the regression test and the existing suite pass.

### 5. Check and document

- **Do:** run every command in `checks`. Record the cause and the fix on the docs page that covers the changed
  code; for a bug that reached users, write `docs/incidents/<YYYY-MM-DD>-<id>.md`.
- **Done when:** all `checks` commands exit 0 and the docs page names the root cause and the regression test.
