---
trigger: manual
glob: code-style-guide
description: language-agnostic code style principles for readable and maintainable code
---

# Code Style Rule

**Rules:**

- **Naming:** Use meaningful, intention-revealing names. Avoid abbreviations except well-known ones (`id`, `url`, `http`).
- **Functions:** Single responsibility — one function does one thing. Maximum ~30 lines; extract if longer.
- **DRY:** Do not Repeat Yourself — extract duplicated logic into shared utilities.
- **Comments:** Code should be self-documenting. Comments explain *why*, not *what*. Remove commented-out code.
- **Magic values:** No magic numbers or strings — use named constants or enums.
- **Error handling:** Handle errors explicitly; never silently swallow exceptions.
- **Immutability:** Prefer immutable data structures where possible.
- **Depth:** Avoid deeply nested code (>3 levels); use early returns/guard clauses.
- **File size:** No file over ~400 lines; split into modules if larger.
- **Consistency:** Follow the existing style of the codebase for the language in use.
- Follow language-specific style guides:
  - Python: PEP 8
  - JavaScript/TypeScript: Airbnb or Standard JS
  - Go: Effective Go

**Violations:**

- Single-letter variable names outside of loop indexes.
- Functions with more than one level of abstraction mixing.
- Hardcoded configuration values in source code.
- TODO comments left in production code for more than one sprint.
