---
name: develop-feature
type: workflow
trigger: /develop-feature
description: Turn a feature request into working code with tests and an up-to-date feature docs page.
inputs:
  - feature_request
  - acceptance_criteria
outputs:
  - code
  - tests
  - docs_page
selection:
  general: true
  use-when: "The request asks to build, add or change behaviour in code: a feature, an endpoint, a small program or script, or any coding task that no narrower workflow fits."
  avoid-when: "The request only asks to diagnose a bug, review a diff, restructure code without behaviour change, or change infrastructure."
uses-skills: []
related-rules:
  - code-style-guide.md
  - docs-layout.md
  - readme-sync-guide.md
checks:
  - make lint
  - make test
artifacts:
  - docs/<feature>/README.md
---

# Develop a feature

Example request: Add subscription cancellation: DELETE /subscriptions/{id} records a reason and keeps access until the period ends.

## Steps

### 1. Describe the current behaviour and the target

- **Do:** read the code paths the request touches and the docs page whose `covers:` matches them. Write
  numbered acceptance criteria and an explicit out-of-scope list into `docs/<feature>/README.md`. Ask the user
  only when a criterion has two plausible meanings.
- **Done when:** each criterion maps to one planned test, and the feature page has a `covers:` key.

### 2. Write the failing tests

- **Do:** add tests for every acceptance criterion at the lowest useful level (unit first, then API or
  integration). Run them.
- **Done when:** the new tests fail for the expected reason and the existing tests still pass.

### 3. Implement

- **Do:** change the smallest set of modules that makes the tests pass. Follow the rules that `paths:` loads
  for the touched files. Keep configuration in settings, not in code.
- **Done when:** the new tests pass and `git diff --stat` lists only files the criteria need.

### 4. Check and document

- **Do:** run every command in `checks`. Update the feature page (design, contracts, risks, status
  `implemented`) and `README.md` when setup or usage changed. Add a `CHANGELOG.md` line for a visible change.
- **Done when:** all `checks` commands exit 0 and the docs coverage check passes for the changed paths.
