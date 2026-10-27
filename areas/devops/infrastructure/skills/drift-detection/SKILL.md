---
name: drift-detection
description: "Procedure to detect and resolve drift between Terraform/OpenTofu code, state, and real infrastructure with plan -detailed-exitcode, import, and refresh-only. Use when a plan shows unexpected changes or when you set up scheduled drift checks."
---

# Terraform drift: detect and resolve

Drift means the real resources differ from the code. Resolve it in code; do not hide it.

## 1. Detect

```bash
terraform init -input=false
terraform plan -input=false -lock=false -detailed-exitcode -out=drift.tfplan
echo $?   # 0 = no changes, 1 = error, 2 = changes (drift or unapplied code)
terraform show -no-color drift.tfplan > drift.txt
```

Use `tofu` instead of `terraform` if the project uses OpenTofu. Run against every environment directory or
workspace that the task names.

## 2. Classify each changed resource

Read `drift.txt` and sort every resource into one class:

1. **Unapplied code** — the code changed on the default branch but nobody applied it. Check `git log` for the
   module. Resolution: apply through the normal pipeline.
2. **Manual change** — someone changed the resource in the console or with a CLI. Check the cloud audit log
   (CloudTrail, GCP Audit Logs, Azure Activity Log) for the actor and time.
3. **Provider-side default** — the provider or service sets a value the code does not set, and the plan shows it
   on every run. Resolution: set the value in code, or add the attribute to `lifecycle { ignore_changes = [...] }`
   with a comment that names the reason.
4. **Resource outside state** — the resource exists but state does not track it.

## 3. Resolve

- Manual change that must stay: copy the value into the code, then run `plan` again until it shows no change.
- Manual change that must go: keep the code. The next apply reverts it. Ask the user first before that apply.
- Resource outside state: add an `import` block and plan:

```hcl
import {
  to = aws_s3_bucket.logs
  id = "group-service-logs"
}
```

- Changed outputs or data sources only: run `terraform apply -refresh-only` to update state. Ask the user first;
  it writes state.
- Never run `terraform state rm` to make drift disappear unless the user wants to stop managing the resource.

## 4. Verify

1. Run step 1 again. The exit code must be `0`, or every remaining change must be a planned code change.
2. Commit the code changes with the drift cause in the commit body.

## 5. Schedule the check (optional)

- GitLab: a scheduled pipeline job runs step 1 and fails on exit code `2`. Use a read-only cloud role.
- GitHub: a workflow with `on: schedule` runs the same job with OIDC credentials for a read-only role.
- Send the failure to the team channel or open an issue with `drift.txt` attached. Do not apply from the
  scheduled job.
