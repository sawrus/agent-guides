---
trigger: manual
glob: git-workflow-guide
description: enforce clean git branching, commit, and pull request practices
---

# Git Workflow Rule

**Rules:**

- Use one branch per task; branch name format: `<type>/<task-id>-<slug>` (matches the root AGENTS.md core).
- Branch types: `feat/`, `fix/`, `hotfix/`, `chore/`, `docs/`, `refactor/`, `release/`.
- Direct commits to `main`/`master` are forbidden; all changes merged via Pull/Merge Request.
- Commit messages follow Conventional Commits format: `<type>(<scope>): <subject>`.
  - Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`.
- Keep commits atomic — one logical change per commit.
- Squash or rebase before merging to keep linear history.
- Tag releases with semantic versions: `v<major>.<minor>.<patch>`.
- Maintain `.gitignore` — never commit secrets, build artifacts, or IDE configs.
- Use `.pre-commit-config.yaml` to run lint/format/tests before every commit.

**Violations:**

- Committing directly to protected branches.
- Vague commit messages like "fix", "wip", "update".
- Missing task/issue reference in branch name or commit body.
- Committed secrets or environment files.
