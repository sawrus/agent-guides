---
trigger: always_on
glob: code-quality-guide
description: enforce code formatting, linting, and static typing after code changes
---

# Code Quality Rule

**Rules:**

- After writing or modifying code, always run formatters and linters.
- Execute `make format` and fix all formatting issues.
- Execute `make lint` and fix all lint/type errors until passed.
- For Python projects, use the following tools via Poetry:
    - `ruff` — linting
    - `black` — code formatting
    - `mypy` — static type checking
- All tools must be installed and run inside the project venv via Poetry.

**Violations:**

- Skipping `make format` or `make lint`.
- Ignoring formatter or linter errors.
- Running tools outside venv.
- Missing ruff/black/mypy in Poetry dependencies.