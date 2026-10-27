---
name: refactor-module
type: workflow
trigger: /refactor-module
description: Restructure a module without changing its observable behaviour, guarded by tests.
inputs:
  - module_path
  - refactoring_goal
outputs:
  - refactored_code
  - characterization_tests
selection:
  general: false
  use-when: "The request asks to restructure, extract, rename, split or clean up existing code while keeping its behaviour the same."
  avoid-when: "The request also changes behaviour or adds a feature; use the feature workflow."
uses-skills: []
related-rules:
  - code-style-guide.md
  - lint-format-guide.md
checks:
  - make lint
  - make test
---

# Refactor a module

Example request: Move the business logic from OrderController into OrderService.

## Steps

### 1. Pin the current behaviour

- **Do:** list the public entry points of the module and their callers (`grep -rn`). Run the tests that cover
  them and measure coverage of the module.
- **Done when:** every public entry point has at least one passing test, or you add characterization tests that
  record the current outputs, including odd ones.

### 2. Plan small steps

- **Do:** split the refactoring into steps that each keep the build green: extract, move, rename, then delete.
  Keep public names and signatures unless the request asks to change them.
- **Done when:** the plan lists each step and the callers it touches.

### 3. Refactor step by step

- **Do:** apply one step, run the module tests, and commit. Do not fix bugs you find on the way; list them.
- **Done when:** each step ends with the tests green and the diff contains no behaviour change.

### 4. Check

- **Do:** run every command in `checks`. Compare the public API before and after (exported names, routes,
  CLI flags). Add the commit trailer `Docs-Not-Needed: refactoring without behaviour change` when no docs
  page needs an update.
- **Done when:** all `checks` commands exit 0 and the public API is unchanged.
