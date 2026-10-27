---
description: Git hygiene beyond the core branch and commit format — ignores, hooks, history, and release tags.
trigger: manual
---

# Git hygiene

- Keep one logical change per commit; do not mix a refactoring and a behaviour change in one commit.
- Add build output, virtual environments, IDE folders, and `.env` files to `.gitignore`.
- Run the hooks of `.pre-commit-config.yaml` when the repository has one; never commit with `--no-verify`.
- Rebase a feature branch on the target branch before merge; never force-push a shared or protected branch.
- Tag releases as `v<major>.<minor>.<patch>` on the release commit.
- Do not rewrite history that is already pushed to `main` or a release branch.
- Remove a committed secret by rotating it first; deleting the commit alone does not make the secret safe.
