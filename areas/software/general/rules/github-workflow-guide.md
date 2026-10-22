---
trigger: glob
paths:
  - ".github/**"
glob: github-workflow-guide
description: GitHub-specific workflow practices for Actions, PRs, and releases
---

# GitHub Workflow Rule

**Rules:**

- Define CI/CD pipelines as GitHub Actions workflows in `.github/workflows/`.
- Workflow files named descriptively: `ci.yml`, `release.yml`, `deploy-staging.yml`.
- Every PR must pass all CI checks before merging (branch protection rules enforced).
- Use environment secrets from GitHub Secrets — never hardcode credentials.
- Use `actions/checkout@v4` and pin all third-party actions to a specific SHA.
- Use reusable workflows (`workflow_call`) to avoid duplication across pipelines.
- Apply branch protection: require PR review, status checks, and no force-pushes to `main`.
- Use GitHub Environments for staged deployments (staging → production).
- Automate releases with tags: push to `vX.Y.Z` triggers release pipeline.
- Use Dependabot for automated dependency updates (`.github/dependabot.yml`).

**Violations:**

- Workflows that run with `GITHUB_TOKEN` permissions broader than needed.
- Unpinned third-party Actions (security risk).
- Manual deployments bypassing CI pipeline.
- Secrets hardcoded in workflow files.
