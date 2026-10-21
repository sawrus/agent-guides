---
trigger: glob
paths:
  - ".pre-commit-config.yaml"
  - "pyproject.toml"
  - "setup.cfg"
  - ".editorconfig"
  - ".eslintrc*"
  - "eslint.config.*"
  - ".prettierrc*"
  - ".golangci.yml"
glob: lint-format-guide
description: enforce consistent linting and auto-formatting across all code
---

# Linting & Formatting Rule

**Rules:**

- Every project must configure a linter and auto-formatter appropriate to the language.
- Common tooling by language:
  - **Python:** `ruff` (lint + format) or `flake8` + `black` + `isort`
  - **JavaScript/TypeScript:** `eslint` + `prettier`
  - **Go:** `golangci-lint` + `gofmt`
  - **Shell:** `shellcheck`
- Linter and formatter config stored in the repo (`.eslintrc`, `pyproject.toml`, `.golangci.yml`).
- Zero lint errors policy — CI fails on any lint warning treated as error.
- Auto-format on save configured in project settings (`.editorconfig`, IDE config).
- Pre-commit hooks run formatter then linter before every commit (`.pre-commit-config.yaml`).
- `make lint` runs the linter; `make fmt` runs the formatter.
- Format check (not just lint) runs in CI to catch unformatted code.

**Violations:**

- Disabling lint rules with inline suppressions without a documented reason.
- CI pipeline that does not fail on lint errors.
- Inconsistent formatting between contributors.
- Missing `.editorconfig` causing whitespace/indentation inconsistencies.
