---
name: gitlab-ci-patterns
description: "Procedure to add or change a GitLab CI pipeline: validate .gitlab-ci.yml, structure jobs with rules/needs/include, cache, and debug a failed job. Use when you edit .gitlab-ci.yml or files under .gitlab/ci/."
---

# GitLab CI: change and debug a pipeline

## 1. Read the current pipeline

1. Open `.gitlab-ci.yml` and every file it pulls in with `include:` (`local`, `project`, `template`, `component`).
2. List the stages, the jobs per stage, and which jobs run on merge requests, on the default branch, and on tags.
3. If the project uses CI components or a shared template project, change the caller first. Change the shared
   template only when the task says so.

## 2. Make the change

1. Put job conditions in `rules:`. Do not add `only:` or `except:`.
2. Express job order with `needs:` when a job does not need the whole previous stage.
3. Reuse setup with `extends:` or `!reference`; do not copy a `script:` block into a second job.
4. Pin every `image:` to a version tag or a digest. Do not use `latest`.
5. Set `timeout:` on jobs that can hang (integration tests, deploys).
6. Set `interruptible: true` on test jobs so a new push cancels the old pipeline.
7. Cache dependencies with a key that changes with the lock file:

```yaml
cache:
  key:
    files: [poetry.lock]   # go.sum, pom.xml, package-lock.json
  paths: [.venv/]
  policy: pull-push        # use `pull` in jobs that only read the cache
```

8. Pass build outputs with `artifacts:` and an `expire_in:` value. Use `artifacts:reports:junit` for test results.
9. Read secrets from CI/CD variables (masked and protected) or from `id_tokens:` with OIDC. Never write a secret
   into the YAML.
10. Put deploy jobs on `environment:` with `rules:` that limit them to protected branches or tags. A production
    deploy job uses `when: manual`; ask the user first before you run it.

## 3. Validate before you push

1. Lint the file with the API or the CLI:

```bash
glab ci lint                       # uses the project CI lint endpoint
glab ci lint --dry-run --ref main  # simulate a pipeline on a branch
```

2. If `glab` is not available, open CI/CD > Editor > Validate in the project UI.
3. Check that each changed job has the expected `rules:` outcome on a merge request and on the default branch.

## 4. Debug a failed job

1. Get the log: `glab ci view` or `glab ci trace <job-id>`.
2. Find the first error line, not the last one.
3. Decide the cause class:
   - **Script error** — reproduce locally with the same image: `docker run --rm -it -v "$PWD":/w -w /w <image> sh`.
   - **Missing variable** — check that the variable is defined for this environment and that protected
     variables are not used on an unprotected branch.
   - **Cache or artifact** — check the cache key and the `needs:`/`dependencies:` list.
   - **Runner** — check `tags:` against the available runners; a job stuck in `pending` has no matching runner.
   - **Flaky test** — rerun once. If it passes, open an issue for the flaky test; do not add `retry:` to hide it.
4. Fix the cause in the repository and push. Do not change the job to `allow_failure: true` to make the
   pipeline green.

## 5. Done

- The lint passes and a pipeline on the branch is green.
- The merge request description names the jobs that changed and why.
