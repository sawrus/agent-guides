---
trigger: always_on
glob: git-versioning-guide
description: enforce traceable git history, versioning, and automated validation
---

# Git & Versioning Rule

**Rules:**

- Use dedicated feature branch per Task; branch name includes Task ID.
- Direct commits to main/master forbidden; merge only after all checks pass.
- Update `CHANGELOG.md` with Task ID and semantic version.
- For python projects: Bump version in `pyproject.toml`; follow semantic versioning (major.minor.patch).
- `.pre-commit-config.yaml` mandatory; hooks run before commit (format, lint, unit tests); failing commits rejected.
- Maintain `.gitignore`/`.dockerignore`; ignore `.*` and `__*__`.

**Violations:**

- Commits without Task context.
- Missing changelog or version bump.
- Bypassing pre-commit hooks.
- Unverified or failing commits.
