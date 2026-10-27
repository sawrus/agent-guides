---
name: iac-change
type: workflow
trigger: /iac-change
description: Provision, change, fix drift in, or destroy infrastructure through Terraform or Ansible with a reviewed plan.
inputs:
  - environment
  - requested_change
outputs:
  - iac_change
  - reviewed_plan
  - docs_page
selection:
  general: false
  use-when: "The request asks to provision, change, import, fix drift in, or destroy cloud or server infrastructure defined in Terraform, OpenTofu or Ansible."
  avoid-when: "Kubernetes workload manifests or Helm values only; use the workload workflow."
uses-skills:
  - terraform-modules
  - drift-detection
related-rules:
  - iac-standards.md
  - state-management.md
  - immutability.md
  - secret-hygiene.md
  - ansible-standards.md
checks:
  - terraform fmt -check -recursive
  - terraform validate
artifacts:
  - docs/<environment>.md
---

# Change infrastructure as code

Example request: Provision a staging environment with Terraform: private network 10.20.0.0/16, three worker VMs, and one load balancer.

## Steps

### 1. Read the current state

- **Do:** find the root module and backend for the environment. Run `terraform init` and
  `terraform plan -detailed-exitcode -lock=false` against the current code. For Ansible, run
  `ansible-playbook --check --diff` with the target inventory.
- **Done when:** you know whether the code and the real infrastructure match (exit code 0 or 2) and list any drift.

### 2. Change the code

- **Do:** follow the step that matches the request:
  provision or change — edit modules and variables with pinned provider and module versions;
  drift — decide per resource whether code or reality is right, then update code or use `import` and `moved` blocks;
  destroy — remove the resources from code and check `prevent_destroy` and backups first.
- **Done when:** `terraform fmt -check` and `terraform validate` pass, and secrets come only from variables or
  a secret store.

### 3. Review the plan

- **Do:** run `terraform plan -out=tfplan` and read every replace and destroy action. Explain each one. For a
  destroy or replace of a stateful resource (database, volume, bucket), name the backup and the restore test.
- **Done when:** the plan shows only the expected adds, changes, and destroys.

### 4. Apply

- **Do:** ask the user first before `terraform apply`, `terraform destroy`, `terraform state` commands, or a
  non-check Ansible run. Apply only the reviewed `tfplan`. Prefer the CI pipeline apply job when one exists.
- **Done when:** the apply finishes and a new `terraform plan -detailed-exitcode` returns 0.

### 5. Document

- **Do:** update the environment docs page (resources, inputs, outputs, how to recreate). Run every command
  in `checks`.
- **Done when:** all `checks` commands exit 0 and the docs page matches the applied state.
