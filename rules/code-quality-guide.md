---
trigger: always_on
glob: code-quality-guide
description: enforce code formatting, linting, and static typing after code changes
---

# Code Quality Rule

**Rules:**

- After writing or modifying code, always run formatters and linters.
- Execute formatting tools and fix all formatting issues.
- Execute linting tools and fix all lint/type errors until passed.
- For Python projects, use standard tools (e.g. `ruff`, `black`, `mypy`) via the project's dependency manager.
- All tools must be installed and run inside the project's virtual environment.

**Violations:**

- Skipping formatting or linting.
- Ignoring formatter or linter errors.
- Running tools outside the virtual environment.
- Missing standard quality tools in dependencies.
