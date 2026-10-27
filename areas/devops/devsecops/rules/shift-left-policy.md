---
description: Security scan jobs that CI must run, their severity thresholds, and the fix deadlines per severity.
paths:
  - ".gitlab-ci.yml"
  - "**/.gitlab-ci.yml"
  - ".github/workflows/**"
  - ".pre-commit-config.yaml"
  - ".gitleaks.toml"
  - ".semgrep.yml"
---

# Shift-left security

- Run a secret scan (`gitleaks` or `trufflehog`) in a pre-commit hook and in CI on every merge request.
- Run SAST (`semgrep` or the GitLab SAST template) in CI on every merge request.
- Run a dependency scan (`trivy fs .`, `osv-scanner`, or the ecosystem audit command) before the build job.
- Run `trivy image` on the built image before it is pushed to a release registry.
- Run `syft` to create an SBOM for every release image and attach it with `cosign attest`.
- Run `cosign verify` on the image in the deploy job before rollout.
- Fail the merge request pipeline and the deploy job on any `Critical` or `High` finding.
- Post `Medium` findings as a merge request comment; do not block on `Medium` or `Low` findings.
- Set the fix deadline for `Critical` findings (CVSS 9.0–10.0) to the same day.
- Set the fix deadline for `High` findings (CVSS 7.0–8.9) to 72 hours.
- Create a ticket with a 2-week deadline for every `Medium` finding (CVSS 4.0–6.9).
- Document every exception in the scanner ignore file with a reason, a ticket, an owner, and an expiry of at most 30 days.
- Add an inline suppression with a reason for every SAST false positive; never disable a scanner rule globally for one finding.
