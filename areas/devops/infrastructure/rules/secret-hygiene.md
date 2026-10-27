---
description: Keep secrets out of Terraform and Ansible code, variables, and state.
paths:
  - "**/*.tf"
  - "**/*.tfvars"
  - "**/group_vars/**"
  - "**/host_vars/**"
  - "**/inventory/**"
---

# Secret hygiene in IaC

- Never write a password, token, or private key as a literal in a `.tf`, `.tfvars`, or Ansible vars file.
- Read secrets at apply time from a secret manager data source (`aws_secretsmanager_secret_version`, `vault_kv_secret_v2`, `google_secret_manager_secret_version`).
- Prefer generated secrets (`random_password`) written straight to the secret manager over values passed in variables.
- Set `sensitive = true` on every variable and output that holds a secret; never override it to `false`.
- Encrypt Ansible secrets with `ansible-vault` or look them up from Vault; never commit plain-text secrets in `group_vars/` or `host_vars/`.
- Inject runtime secrets into Kubernetes with External Secrets Operator or a CSI secret driver; do not set them as Terraform string literals in pod env.
- Add a `gitleaks` or `trufflehog` pre-commit hook and CI job to every infrastructure repository.
- Rotate a leaked secret first, then remove it from Git history with `git filter-repo`, then check the access logs for its use.
