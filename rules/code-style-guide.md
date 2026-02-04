---
trigger: always_on
glob: code-style-guide
description: readable, maintainable, and safe-to-automate code
---

# Code Style Rule

**Goal:** readable, predictable, safe to automate, cheap to delete.

**Rules:**

- Follow language/framework conventions; keep it simple (KISS).
- Centralize config; use polymorphism over conditionals; isolate async/multithreading.
- Use dependency injection; follow Law of Demeter.
- Be consistent: names, formatting, boundary encapsulation.
- Functions: do one thing, ≤10 lines, few args, no side effects/flags.
- Replace magic numbers with constants; keep related code together.
- Catch specific exceptions; never base Exception; explain intent.
- Tests: readable, fast, isolated, repeatable; 1 assertion per test.
- Standards: strict type hints, Pydantic for models, external APIs via `tools/`.

**Violations:** rigidity, fragility, duplication, hidden execution order, complexity.