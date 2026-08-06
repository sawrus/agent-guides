---
name: pipeline-debug
type: workflow
trigger: /pipeline-debug
description: Diagnose and fix a failing CI/CD pipeline — from error classification to root cause and verified fix.
inputs:
  - pipeline_url_or_job_id
  - error_description
outputs:
  - root_cause_summary
  - pipeline_fix
roles:
  - devops-engineer
execution:
  initiator: devops-engineer
agent: devops-engineer
related-rules:
  - pipeline-standards.md
uses-skills:
  - github-actions-patterns
  - gitlab-ci-patterns
quality-gates:
  - pipeline passes on fixed branch before merging fix
---

## Steps

### 1. Classify Failure — `@devops-engineer`
- **Input:** pipeline_url_or_job_id and error_description from the workflow inputs.
- Fetch full logs; identify failing stage and step
- Categories: dependency install failure / test failure / auth failure / build failure / deploy timeout
- Check: is this a flaky test or a real regression? (re-run once to distinguish)
- **Done when:** failure mode and stage identified

### 2. Diagnose by Category — `@devops-engineer`
- **Input:** failure category and failing stage from step 1.

**Auth failure (registry, cloud, K8s):**
- Check secret expiry / OIDC trust policy / runner network access
- `kubectl auth can-i` / `aws sts get-caller-identity` in job debug step

**Dependency install failure:**
- Cache key stale? Lock file changed? Private registry down?
- Add `--verbose` flag, check resolver output

**Test failure:**
- Run tests locally with same env vars
- Check for env-dependent tests (timezone, locale, missing fixture)

**Build/Docker failure:**
- Check base image digest changed (pin to digest)
- Layer cache invalidation causing unexpected rebuild

**Deploy timeout:**
- Check `helm status` / `kubectl rollout status` in target namespace
- Look at pod events for the deployment being rolled out

- **Done when:** root cause identified and confirmed for the failing category.

### 3. Fix & Verify — `@devops-engineer`
- **Input:** root cause diagnosis from step 2.
- Apply fix on feature branch; push to trigger CI
- Confirm the previously failing stage now passes
- No unrelated regressions in other stages
- **Done when:** full pipeline green on fix branch

### 4. Merge & Monitor — `@devops-engineer`
- **Input:** green fix branch from step 3.
- Merge fix; confirm pipeline green on main
- If flaky test: add to quarantine list; file follow-up ticket with `flaky-test` label
- **Done when:** pipeline green on main; root cause documented in the ticket.

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /pipeline-debug"])
  role_1["devops-engineer"]
  step_1["1. Classify Failure"]
  step_2["2. Diagnose by Category"]
  step_3["3. Fix & Verify"]
  step_4["4. Merge & Monitor"]
  exit(["Pipeline green + root cause documented in ticket = debug complete. Recurrin..."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> exit
  role_1 -. owns .-> step_1
  role_1 -. owns .-> step_2
  role_1 -. owns .-> step_3
  role_1 -. owns .-> step_4
```
<!-- agent-diagram:end -->

## Exit
Pipeline green + root cause documented in ticket = debug complete. Recurring root causes that warrant a pipeline change should be filed via /onboard-repo or a `docs/ci-cd.md` update.

**Next:** terminal — no follow-up workflow.
