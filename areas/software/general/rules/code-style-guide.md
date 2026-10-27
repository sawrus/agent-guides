---
description: Code style checks that apply to source files in any language.
paths:
  - "**/*.py"
  - "**/*.go"
  - "**/*.java"
  - "**/*.kt"
  - "**/*.ts"
  - "**/*.js"
  - "**/*.rs"
  - "**/*.sh"
---

# Code style

- Follow the formatter and linter config of the repository; do not reformat lines that the change does not touch.
- Name functions, variables, and types after intent; no single-letter names outside loop indexes and short lambdas.
- Keep functions under about 40 lines and nesting at 3 levels or less; use early returns.
- Replace magic numbers and strings with named constants or enums.
- Handle every error explicitly; never use an empty `except:`/`catch {}` block or ignore a returned `error`.
- Remove commented-out code and debug output (`print`, `console.log`) before commit.
- Write comments that explain why; do not restate what the next line does.
- Add a ticket id to every new `TODO` comment.
- Do not hardcode hosts, credentials, or environment names in source files; read them from configuration.
- Keep files under about 400 lines; split a larger file by responsibility in the same change only when the task asks for it.
- Do not add a dependency for a function that is under 20 lines to write.
