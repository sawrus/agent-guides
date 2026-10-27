---
description: Secret storage, scanning, rotation, and leak response for application repositories.
paths:
  - "**/.env*"
  - ".gitleaks.toml"
  - ".pre-commit-config.yaml"
  - "**/secrets/**"
  - "**/config/**"
---

# Secrets policy

- Never commit passwords, API keys, tokens, or private keys, including in `.env.example`; use placeholder values.
- Run `gitleaks` or `trufflehog` as a pre-commit hook and as a CI job on every merge request.
- Store secrets in a secret manager (Vault or the cloud provider's secret service) and read them at runtime.
- Set an expiry for every secret and rotate it at least every 90 days.
- Enable audit logging for secret reads in the secret manager.
- Revoke a leaked secret within 30 minutes, then rotate secrets with the same scope and check access logs for the exposure window.
- Remove a leaked secret from git history with `git filter-repo` only after revocation.
