---
description: Makefile targets and conventions that give every project the same developer commands.
paths:
  - "Makefile"
  - "**/Makefile"
  - "**/*.mk"
---

# Makefile

- Keep a `Makefile` at the repository root with the targets `help`, `install`, `test`, `lint`, `fmt`, and `clean`.
- Add `run` or `dev` when the project starts a local service.
- Declare every target that does not create a file in `.PHONY`.
- Add a `## description` comment to every public target and make `help` print them.
- Put tool names, image names, and versions in variables (`PYTHON ?= python3`) so a caller can override them.
- Compose larger targets from smaller ones (`ci: lint test`); do not copy the same command into two targets.
- Use POSIX shell syntax in recipes, or set `SHELL := bash` at the top when a recipe needs bash.
- Do not hardcode absolute paths from one machine; use `$(CURDIR)` or relative paths.
- Make `make test` and `make lint` exit non-zero on failure; never append `|| true` to a check.
