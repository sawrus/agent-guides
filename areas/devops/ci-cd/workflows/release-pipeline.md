---
name: release-pipeline
type: workflow
trigger: /release-pipeline
description: Run a production release with supply-chain verification, database compatibility controls, progressive delivery, and measurable rollback criteria.
inputs:
  - version (semver: v1.2.3)
  - release_notes (optional)
  - risk_level (low|medium|high)
outputs:
  - published_release
  - deployed_version
  - deployment_report
roles:
  - devops-engineer
  - developer
  - team-lead
  - pm
  - qa
execution:
  initiator: developer
agent: developer
related-rules:
  - pipeline-standards.md
  - quality-gates.md
  - supply-chain-security.md
uses-skills:
  - github-actions-patterns
  - artifact-management
  - pipeline-security
quality-gates:
  - all CI gates pass on release commit
  - image signed, provenance generated, and SBOM attached before deploy
  - staging deploy healthy >= 15 min before production gate
  - manual approval from team-lead for production
  - rollback criteria defined before canary starts
---

## Steps

### 1. Release Readiness and Freeze Check — `@team-lead` + `@pm`
- **Input:** version, risk_level, and release_notes from the workflow inputs.
- **Actions:**
  - Confirm no active P0/P1 incidents.
  - Confirm release window is approved (freeze policy respected).
  - Assign release owner, rollback owner, and incident commander.
  - Confirm stakeholder communication plan (`#deployments`, support, customer-facing status if needed).
  - Confirm `CHANGELOG.md` entry for `v${VERSION}` is merged — production release requires a CHANGELOG entry plus the version tag created in step 3.
- **Done when:** readiness checklist signed by team-lead and CHANGELOG entry present.

### 2. Database Compatibility Gate — `@developer` + `@devops-engineer`
- **Input:** signed readiness checklist from step 1.
- **Actions:**
  - Validate schema changes follow **expand/contract** strategy.
  - Forbid destructive migrations in same release as dependent app change.
  - Ensure old and new app versions can run concurrently during canary.
  - Prepare rollback-safe migration plan.
- **Done when:** DB compatibility checklist is green.

### 3. Tag Release — `@developer`
- **Input:** green DB compatibility checklist from step 2.
```bash
git tag -a v${VERSION} -m "Release v${VERSION}: ${RELEASE_NOTES}"
git push origin v${VERSION}
```
- **Done when:** tag-triggered pipeline starts.

### 4. CI Release Pipeline (automated) — `@devops-engineer`
- **Input:** release tag `v${VERSION}` from step 3.
- **Stages:**
  1. `validate` — lint/test/type/security checks.
  2. `build` — immutable image digest produced.
  3. `sign` — keyless `cosign sign` on digest.
  4. `attest` — SLSA provenance generated.
  5. `sbom` — CycloneDX/SPDX SBOM generated + attached.
  6. `verify` — signature/provenance identity checks.
  7. `publish` — publish artifact and release notes.
- **Done when:** pipeline green with verifiable artifact metadata.

### 5. Deploy Staging — `@devops-engineer`
- **Input:** verified, signed artifact digest from step 4.
```bash
helm upgrade --install order-service charts/order-service \
  --set image.digest=sha256:${DIGEST} \
  --namespace staging \
  --atomic --timeout 10m
```
- Run smoke + integration critical path tests.
- Observe golden signals for at least 15 minutes.
- **Done when:** staging stable and tests pass.

### 6. Production Gate — `@team-lead` + `@qa`
- **Input:** staging validation results from step 5.
- **Actions:**
  - Confirm error budget not exhausted.
  - Confirm rollback command and previous digest ready.
  - Confirm canary SLO thresholds and observation duration are set.
- **Done when:** manual approval is recorded.

### 7. Canary Deployment — `@devops-engineer`
- **Input:** recorded production approval from step 6.
- **Sequence:**
  - 5% traffic for 10 min.
  - 25% traffic for 15 min.
  - 50% traffic for 15 min (high-risk releases only).
  - 100% traffic only if all gates pass.
- **Automatic rollback triggers (example baseline):**
  - 5xx rate > 1% for 5 min,
  - p99 latency regression > 20% for 10 min,
  - fast burn-rate alert firing (>14.4x, 1h window).
- **Done when:** 100% traffic served by the new version with no rollback trigger fired.

### 8. Feature Flag Progression — `@developer` + `@qa`
- **Input:** healthy canary at 100% traffic from step 7.
- Keep high-risk features behind flags during rollout.
- Enable by cohorts (internal → 5% users → 25% → 100%).
- Roll back by disabling flag if service health degrades without binary rollback.
- **Done when:** all cohorts enabled with service health stable, or flag rolled back.

### 9. Post-Deploy Validation — `@qa` + `@pm`
- **Input:** fully rolled-out release with flag progression from step 8.
- Run production smoke checks.
- Verify business KPIs (conversion, checkout success, error funnel).
- Publish deployment report with links to metrics, logs, and release artifact metadata.
- **Done when:** deployment report published and business KPIs within expected range.

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /release-pipeline"])
  role_1["team-lead"]
  role_2["pm"]
  role_3["developer"]
  role_4["devops-engineer"]
  role_5["qa"]
  step_1["1. Release Readiness and Freeze Check"]
  step_2["2. Database Compatibility Gate"]
  step_3["3. Tag Release"]
  step_4["4. CI Release Pipeline (automated)"]
  step_5["5. Deploy Staging"]
  step_6["6. Production Gate"]
  step_7["7. Canary Deployment"]
  step_8["8. Feature Flag Progression"]
  step_9["9. Post-Deploy Validation"]
  exit(["Release is complete when 100% traffic is healthy, post-deploy checks pass,..."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> step_6
  step_6 --> step_7
  step_7 --> step_8
  step_8 --> step_9
  step_9 --> exit
  role_1 -. owns .-> step_1
  role_2 -. owns .-> step_1
  role_3 -. owns .-> step_2
  role_4 -. owns .-> step_2
  role_3 -. owns .-> step_3
  role_4 -. owns .-> step_4
  role_4 -. owns .-> step_5
  role_1 -. owns .-> step_6
  role_5 -. owns .-> step_6
  role_4 -. owns .-> step_7
  role_3 -. owns .-> step_8
  role_5 -. owns .-> step_8
  role_5 -. owns .-> step_9
  role_2 -. owns .-> step_9
  step_9 -. iterate if blocked .-> step_1
```
<!-- agent-diagram:end -->

## Rollback

```bash
helm rollback order-service -n production
# or redeploy previous verified digest
```

- Rollback is mandatory when any SLO rollback trigger is met.
- If DB migrations were expanded, execute rollback-safe contract plan only after traffic is stable.
- At most 2 release re-attempts after a rollback; a third failure freezes the release and escalates to `@team-lead` + `@pm` for a go/no-go decision.

## Exit

Release is complete when 100% traffic is healthy, post-deploy checks pass, and release report is published.

**Next:** terminal — no follow-up workflow.
