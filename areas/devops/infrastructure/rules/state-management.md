---
description: Remote backend, isolation, locking, protection, and safe state operations for Terraform state.
paths:
  - "**/backend.tf"
  - "**/backend*.hcl"
  - "**/versions.tf"
  - "**/terragrunt.hcl"
  - "**/*.tf"
---

# Terraform state management

- Use a remote backend (`s3`, `gcs`, `azurerm`, or HCP Terraform) for every non-local environment.
- Keep one state per `environment/component` key; never share a state between staging and production.
- Use separate buckets (or accounts) for staging and production state.
- Enable state locking (`use_lockfile = true` or `dynamodb_table` for S3; built-in for GCS) and never disable it.
- Enable versioning, encryption with a KMS key (`encrypt = true`, `kms_key_id`), and a public access block on the state bucket.
- Limit state bucket access to CI roles and on-call engineers with MFA.
- Do not read `terraform_remote_state` across environment boundaries; publish shared values to SSM Parameter Store or another key-value store.
- Use `import` blocks (Terraform 1.5+) to adopt existing resources and require `terraform plan` to show no changes after import.
- Prefer `moved` blocks over `terraform state mv`; run `terraform state pull > backup-<date>.tfstate` before any `state mv` or `state rm`.
- Run `terraform force-unlock <LOCK_ID>` only after you confirm that no apply job holds the lock.
- Never delete old state versions from the bucket by hand.
