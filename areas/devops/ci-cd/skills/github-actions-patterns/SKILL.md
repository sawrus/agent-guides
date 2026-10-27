---
name: github-actions-patterns
description: "Procedure to add or change a GitHub Actions workflow: pin actions, set token permissions, cache, reuse workflows, and debug a failed run. Use when you edit files under .github/workflows/."
---

# GitHub Actions: change and debug a workflow

## 1. Read the current workflows

1. List `.github/workflows/*.yml` and the `on:` triggers of each file.
2. Find reusable workflows (`on: workflow_call`) and composite actions under `.github/actions/`.
3. Change the reusable workflow only when the task says so; otherwise change the caller.

## 2. Make the change

1. Set `permissions:` at the top of the workflow to the minimum, for example `contents: read`. Grant more per
   job only where a step needs it.
2. Pin every third-party action to a full commit SHA and keep the version in a comment:
   `uses: actions/checkout@<40-char-sha> # v4.2.2`.
3. Use `actions/setup-python`, `actions/setup-go`, or `actions/setup-java` with their built-in `cache:` input
   before you add a separate `actions/cache` step.
4. Set `timeout-minutes:` on every job.
5. Add `concurrency:` with `cancel-in-progress: true` for pull request workflows.
6. Move steps that two workflows share into a reusable workflow or a composite action.
7. Use `pull_request`, not `pull_request_target`, for code from forks. If `pull_request_target` is required, do
   not check out the fork head in that job.
8. Do not put `${{ github.event.* }}` text such as titles or branch names directly into `run:`; pass it through
   `env:` and quote the variable.
9. Read cloud credentials with OIDC (`permissions: id-token: write`) instead of long-lived secrets.
10. Put deploys behind a GitHub Environment with required reviewers. Ask the user first before you trigger a
    production deploy.

## 3. Validate before you push

```bash
actionlint                      # syntax, expressions, shellcheck of run: blocks
zizmor .github/workflows/       # security findings (optional)
```

If `actionlint` is not installed, run it as a container: `docker run --rm -v "$PWD":/repo -w /repo rhysd/actionlint`.

## 4. Debug a failed run

1. Get the log: `gh run list --limit 5`, then `gh run view <run-id> --log-failed`.
2. Find the first failing step and its first error line.
3. Decide the cause class:
   - **Permissions** — a `403` or `Resource not accessible by integration` needs a `permissions:` entry.
   - **Secret missing** — secrets are empty in workflows from forks and in environments that do not define them.
   - **Cache** — check the cache key inputs; a changed lock file must change the key.
   - **Runner image** — compare the tool versions with the last green run.
4. Rerun failed jobs with debug logs once: `gh run rerun <run-id> --failed --debug`.
5. Fix the cause and push. Do not add `continue-on-error: true` to make the run green.

## 5. Done

- `actionlint` passes and the workflow run on the branch is green.
- No action is referenced by a tag or a branch.
