---
name: release-pipeline
type: workflow
trigger: /release-pipeline
description: Build or fix a CI/CD pipeline that tests, builds, and releases a service through gated environments.
inputs:
  - service
  - pipeline_goal
outputs:
  - pipeline_config
  - docs_page
selection:
  general: false
  use-when: "The request asks to create, fix, speed up or harden a GitLab CI or GitHub Actions pipeline, or to set up build, release and deploy jobs for a service."
  avoid-when: "The request is a security scan of existing code or images only; use the security scan workflow."
uses-skills:
  - gitlab-ci-patterns
  - github-actions-patterns
related-rules:
  - pipeline-standards.md
  - supply-chain-security.md
artifacts:
  - .gitlab-ci.yml
  - .github/workflows/*.yml
---

# Release pipeline

Example request: `/release-pipeline "payments-api v3.8.0: add a gated production deploy with a migration job and automatic rollback"`

## Steps

### 1. Read the current pipeline

- **Do:** open `.gitlab-ci.yml` (and its `include:` files) or `.github/workflows/*.yml`. List stages, jobs,
  triggers, runners, and the last failed job log (`glab ci view`, `gh run view --log-failed`).
- **Done when:** you can describe the current flow from commit to release and name what is missing or failing.

### 2. Change the pipeline

- **Do:** follow `gitlab-ci-patterns` for GitLab or `github-actions-patterns` for GitHub. Keep the order lint →
  test → build → scan → release → deploy. Build the artifact once and promote the same digest to every
  environment. Ask the user first before you change a deploy job that targets production.
- **Done when:** the config passes the linter (`glab ci lint`, `actionlint`) and every job has a timeout.

### 3. Gate the release

- **Do:** add a protected manual or approval gate before production, and a rollback job or documented
  rollback command. Ask the user first before you run any deploy job or change protected environment settings.
- **Done when:** a production deploy cannot start without the gate and green test, build, and scan jobs.

### 4. Prove it on a branch

- **Do:** push to a feature branch and run the pipeline up to the last non-production stage. Fix each failure
  from its job log. Ask the user first if a job could reach a shared or production environment.
- **Done when:** the branch pipeline is green up to staging, and the docs page of the pipeline lists stages,
  gates, variables, and the rollback command.
