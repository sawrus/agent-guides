---
trigger: always_on
glob: readme-sync-guide
description: keep README.md synchronized with the actual codebase after approved changes
---

# README Synchronization Rule

**Rules:**

- Synchronize `README.md` with the current state of the codebase after all approved changes.
- Review the full repository context before updating docs: code, configs, scripts, `Makefile`, Docker, and CI setup.
- Update only factual and technical sections.

**Must update:**

- setup and installation instructions
- environment variables and configuration
- architecture overview (when applicable)
- usage examples (CLI, API, scripts)
- development workflow (`Makefile`, Docker, CI/CD)

**Must ensure:**

- commands and paths in `README.md` match real project files
- instructions are runnable for a new developer
- no references to removed or outdated components
- terminology is consistent with the codebase

**Must NOT:**

- change business/product descriptions unless explicitly requested
- add undocumented or speculative features
- leave placeholders or TODOs

**Definition of Done:**

- a new developer can install the project, run it locally, and understand core architecture from `README.md`
- all documented commands and paths are verified against the repository
- no conflicting or outdated guidance remains
