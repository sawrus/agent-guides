---
description: Keep README.md setup, configuration, and usage sections true to the repository.
paths:
  - "README.md"
  - "**/README.md"
---

# README sync

- Update the setup, configuration, and usage sections of `README.md` in the same change that alters them in code.
- Check that every command in `README.md` exists (`make` target, script path, CLI flag) before you commit.
- List every required environment variable, or link `.env.example`.
- Remove references to deleted files, targets, flags, and services.
- Keep `README.md` runnable for a new developer: install, configure, run, and test commands in that order.
- Do not change product or business descriptions unless the task asks for it.
- Do not document planned features; no placeholders or `TODO` lines in `README.md`.
