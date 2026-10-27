---
description: Linter and formatter configuration, pre-commit hooks, and CI lint gates.
paths:
  - ".pre-commit-config.yaml"
  - "pyproject.toml"
  - "setup.cfg"
  - ".editorconfig"
  - ".golangci.yml"
  - ".golangci.yaml"
  - "checkstyle.xml"
  - "eslint.config.*"
  - ".eslintrc*"
  - ".prettierrc*"
---

# Lint and format

- Configure one formatter and one linter per language in a committed file: `ruff` for Python, `gofmt` and `golangci-lint` for Go, `spotless` or `checkstyle` for Java, `shellcheck` for shell.
- Keep tool versions pinned in the config (`rev:` in `.pre-commit-config.yaml`, plugin versions in the build file).
- Add a `make lint` target that runs the format check and the linter without changing files.
- Add a `make fmt` target that applies the formatter.
- Run the format check and the linter in CI and fail the job on any finding.
- Add a reason comment to every inline suppression (`# noqa: E501  reason`, `//nolint:errcheck // reason`).
- Do not disable a lint rule for the whole repository in the same change that introduces a violation of it.
- Keep `.editorconfig` with charset, line ending, and indentation per file type.
