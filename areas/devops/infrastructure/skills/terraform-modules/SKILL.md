---
name: terraform-modules
description: "Procedure to create or change a Terraform/OpenTofu module: inputs and outputs, version pins, fmt/validate/tflint/test, and safe renames with moved blocks. Use when you edit *.tf files of a module or move resources between modules."
---

# Terraform module: change safely

## 1. Read the module and its callers

1. Open `variables.tf`, `outputs.tf`, `versions.tf`, and `main.tf` of the module.
2. Find every caller: `grep -rn 'source *= *".*<module-name>' --include=*.tf .`
3. If the module is published with a version (registry or git tag), check which versions the callers pin.

## 2. Change the interface

1. Give every new variable a `type`, a `description`, and a `validation` block when the value has a fixed form.
2. Give a new variable a `default` only if every caller can use it. A variable without a default is a breaking
   change for callers.
3. Mark secrets `sensitive = true` in variables and outputs.
4. Do not rename or delete a variable or an output that a caller uses. Add the new one, keep the old one with a
   deprecation note in its `description`, and remove it in a later major version.
5. Pin providers in `versions.tf` with `required_providers` and a `~>` constraint, and set `required_version`.

## 3. Rename or move resources without destroy

A changed resource address makes Terraform destroy and recreate the resource. Add a `moved` block instead:

```hcl
moved {
  from = aws_s3_bucket.this
  to   = aws_s3_bucket.logs
}
```

- Moving a resource into a child module: `from = aws_s3_bucket.logs`, `to = module.logs.aws_s3_bucket.this`.
- Moving between state files needs `terraform state mv` or `removed` + `import` blocks. Ask the user first; it
  writes state.

## 4. Check

```bash
terraform fmt -recursive -check
terraform init -backend=false && terraform validate
tflint --recursive
terraform test            # if the module has tests/*.tftest.hcl
```

1. Add or update a `tests/<name>.tftest.hcl` with `command = plan` for each new input combination.
2. Run `terraform plan` in one caller environment. The plan must show no `destroy` or `forces replacement` line
   that the task did not ask for. Look for `# forces replacement` in the output.
3. If the plan replaces a stateful resource (database, bucket, volume), stop and tell the user.

## 5. Release

1. Update the module `README.md` inputs and outputs table (`terraform-docs markdown table . > README.md` if the
   project uses terraform-docs).
2. If the module is versioned, bump the major version for a breaking interface change, the minor version for a
   new input or output.
3. Applying the change to an environment goes through the pipeline. Ask the user first before any
   `terraform apply`.
