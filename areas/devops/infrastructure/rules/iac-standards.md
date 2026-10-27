---
description: Layout, version pinning, naming, tagging, and review checks for Terraform code.
paths:
  - "**/*.tf"
  - "**/*.tfvars"
  - "**/.terraform.lock.hcl"
  - "**/terragrunt.hcl"
---

# Terraform standards

- Keep reusable modules in `modules/<name>/` without environment-specific values; keep `environments/<env>/` for tfvars and backend config.
- Set `required_version` with an upper bound (for example `">= 1.9, < 2.0"`) in every root module.
- Pin every provider in `required_providers` with a `~>` constraint and commit `.terraform.lock.hcl`.
- Pin module sources to a version tag (`?ref=v1.4.2` or `version = "1.4.2"`); never use `?ref=main` or a branch name.
- Name resources with the pattern `${var.project}-${var.environment}-${var.name}`.
- Add the tags `Project`, `Environment`, `ManagedBy = "terraform"`, `Owner`, and `CostCenter` to every taggable resource (use provider `default_tags` where available).
- Declare `type` and `description` for every variable and `description` for every output.
- Add `validation` blocks for variables with a closed set of values (environment names, sizes).
- Use `for_each` with stable keys instead of `count` for collections of named resources.
- Use `moved` blocks to rename or restructure resources instead of destroy and create.
- Set `prevent_destroy = true` in `lifecycle` for databases, state buckets, and KMS keys.
- Run `terraform fmt -check`, `terraform validate`, and `tflint` in CI on every change.
- Post the `terraform plan` output to the merge request and apply only the reviewed plan file (`terraform apply <planfile>`).
- Apply only from CI; never run `terraform apply` against staging or production from a workstation.
