---
name: release-pipeline
type: workflow
trigger: /release-pipeline
description: Run a full production release — version tagging, changelog generation, image signing, staging validation, canary deploy to production.
inputs:
  - version (semver: v1.2.3)
  - release_notes (optional)
outputs:
  - published_release
  - deployed_version
  - deployment_report
roles:
  - devops-engineer
  - developer
  - team-lead
  - pm
execution:
  initiator: developer
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
  - image signed and SBOM attached before deploy
  - staging deploy healthy ≥ 15 min before production gate
  - manual approval from team-lead for production
---

## Steps

### 1. Pre-Release Checks — `@devops-engineer` + `@team-lead`
- **Actions:**
  - Confirm no active P0/P1 incidents
  - Verify staging is healthy and running the release candidate
  - Run final security scan on release image: `trivy image <image>:<version>`
  - Check dependency review — no new Critical/High CVEs introduced
  - Confirm changelog complete and reviewed
- **Done when:** all checks green; team-lead approves release to proceed

### 2. Tag Release — `@developer`
- **Actions:**
  ```bash
  # Create annotated git tag
  git tag -a v${VERSION} -m "Release v${VERSION}: ${RELEASE_NOTES}"
  git push origin v${VERSION}
  ```
- **Output:** git tag triggers release pipeline in CI
- **Done when:** CI pipeline starts on the tag event

### 3. CI Release Pipeline (automated) — CI system
- **Stages:**
  1. `validate` — lint + test suite must pass on tagged commit
  2. `build` — Docker image tagged with semver + SHA digest
  3. `sign` — `cosign sign` + `syft` SBOM generation + `cosign attach sbom`
  4. `scan` — Trivy image scan on the exact release image; block on Critical/High
  5. `publish` — push to releases registry; create GitHub Release with changelog
- **Done when:** CI pipeline green; release published to registry

### 4. Deploy Staging — `@devops-engineer`
```bash
helm upgrade --install order-service charts/order-service \
  --set image.tag=v${VERSION} \
  --namespace staging \
  --atomic --timeout 5m
```
- Monitor for 15 minutes: error rate, p99 latency, pod restarts
- Run automated smoke test suite against staging
- **Done when:** 15 min stable; smoke tests pass

### 5. Production Gate — `@team-lead` (manual approval)
- Review staging metrics: confirm no anomalies
- Check error budget: confirm budget not exhausted
- Approve in CI platform (GitHub Environment approval / GitLab manual job)
- **Done when:** approval recorded

### 6. Deploy Production (canary) — `@devops-engineer`
```bash
# Canary: 10% traffic to new version
helm upgrade --install order-service charts/order-service \
  --set image.tag=v${VERSION} \
  --set canary.enabled=true \
  --set canary.weight=10 \
  --namespace production \
  --atomic --timeout 5m

# Watch for 5 minutes
# If SLO breach → auto-rollback
# If healthy → progress to 100%
helm upgrade order-service charts/order-service \
  --set image.tag=v${VERSION} \
  --set canary.enabled=false \
  --namespace production \
  --atomic --timeout 5m
```
- **Done when:** 100% traffic on new version; no SLO breaches

### 7. Post-Deploy Validation — `@qa` + `@pm`
- Run production smoke tests
- Verify key business metrics not degraded
- Announce release in #deployments channel

### Rollback (if needed at any step)
```bash
helm rollback order-service -n production
# or: deploy previous version tag explicitly
```

## Exit
Production 100% + smoke tests pass + team notified + deployment report = release complete.
