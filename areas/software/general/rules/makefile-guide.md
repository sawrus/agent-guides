---
trigger: glob
paths:
  - "Makefile"
  - "**/Makefile"
  - "**/*.mk"
glob: makefile-guide
description: Makefile conventions for consistent developer experience across projects
---

# Makefile Conventions Rule

**Rules:**

- Every project must have a `Makefile` at the root for common developer tasks.
- Declare all non-file targets as `.PHONY` to avoid conflicts with files of the same name.
- Standard targets that must be present:
  - `make install` — install dependencies
  - `make dev` — start local development server/environment
  - `make test` — run test suite
  - `make lint` — run linter
  - `make fmt` — auto-format code
  - `make clean` — remove build artifacts and caches
  - `make help` — list all targets with descriptions
- Use `## comment` after target definition for auto-generated help:
  ```makefile
  test: ## Run test suite
      pytest
  ```
- Compose complex commands from simpler targets: `make ci: lint test build`.
- Use variables for configurable values (paths, image names, versions).
- Keep Makefile portable — prefer POSIX shell commands over bash-specific syntax.

**Violations:**

- Undocumented targets with no `help` output.
- Hardcoded paths that break on different developer machines.
- Duplicated commands across targets instead of composing them.
