---
description: Stage order, gates, job settings, and secret handling for GitLab CI and GitHub Actions pipelines.
paths:
  - ".gitlab-ci.yml"
  - "**/.gitlab-ci.yml"
  - ".gitlab/**"
  - "**/*.gitlab-ci.yml"
  - ".github/workflows/**"
  - ".github/actions/**"
---

# Pipeline standards

## Stages and gates

- Keep the stage order `lint` → `test` → `build` → `scan` → `deploy-staging` → `smoke-test` → `deploy-production`.
- Fail the `lint` job on any linter or format error; do not set `allow_failure: true` on lint, test, or scan jobs.
- Block the merge when any unit or integration test fails; keep line coverage of critical paths at 80 % or more.
- Fail the `scan` stage on any Critical or High finding of SAST, dependency, image, or secret scans.
- Tag every built image with the commit SHA (`$CI_COMMIT_SHA`, `${{ github.sha }}`); never push `latest`, `main`, or branch-name tags.
- Deploy to staging automatically after a merge to the default branch, then run the smoke test job against staging.
- Gate the `deploy-production` job with a protected environment and a manual approval; require staging to be healthy for 15 minutes first.
- Set `timeout:` (GitLab) or `timeout-minutes:` (GitHub) on every job.

## GitLab CI

- Use `rules:` for job conditions; do not use `only:` or `except:`.
- Split large pipelines with `include:` templates; keep shared templates in `.gitlab/ci/` or a template project pinned by `ref:`.
- Pin every job `image:` to a version tag or `@sha256` digest; never use `:latest`.
- Use `needs:` to build a DAG instead of waiting for whole stages.
- Set `cache:key:files:` on the lockfile for dependency caches and pass build outputs with `artifacts:` plus `expire_in:`.
- Store credentials in CI/CD variables marked `masked` and `protected`; never write a secret value in `.gitlab-ci.yml`.
- Use `id_tokens:` for cloud and Vault authentication instead of static access keys.
- Run production deploy jobs only on protected branches or tags and with `environment:` set.

## GitHub Actions

- Set a top-level `permissions:` block with `contents: read` and add wider scopes per job only.
- Pin every third-party action to a full commit SHA; keep the version in a trailing comment.
- Use `id-token: write` with OIDC (`aws-actions/configure-aws-credentials`, `google-github-actions/auth`) instead of long-lived cloud keys.
- Read credentials only from `secrets.*` or environment secrets; never echo a secret or dump `env` in a step.
- Use reusable workflows (`workflow_call`) for steps shared across repositories.
- Use GitHub Environments with required reviewers for the production deploy job.
- Add `.github/dependabot.yml` for `github-actions` and the package ecosystem of the repository.

## Pipeline as code

- Keep all pipeline configuration in the repository; do not configure jobs in the CI web UI.
- Run deploy jobs on ephemeral runners without privileged mode unless the job file documents the reason.
- Never store cloud credentials or a kubeconfig on the runner disk after the job ends.
