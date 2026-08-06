---
name: destroy-environment
type: workflow
trigger: /destroy-environment
description: Safely destroy a Terraform-managed environment — pre-checks, approval gate, ordered teardown, and state cleanup.
inputs:
  - environment_name
  - reason (decommission|cost-saving|reset)
outputs:
  - environment_destroyed
  - state_cleaned
roles:
  - devops-engineer
  - team-lead
  - product-owner
execution:
  initiator: devops-engineer
agent: devops-engineer
related-rules:
  - state-management.md
  - immutability.md
uses-skills:
  - terraform-modules
  - state-management
quality-gates:
  - explicit team-lead approval required before any destroy
  - backup of state file taken before destroy
  - production environment requires product-owner sign-off (business sign-off for production destroys)
---

## Steps

### 1. Confirm Scope — `@devops-engineer`
- **Input:** environment_name and reason from trigger inputs
- List all resources to be destroyed: `terraform plan -destroy -var-file=terraform.tfvars`
- Verify: is there **production data** in this environment? (databases, object storage)
- Confirm no active traffic or dependent services
- **Stop here if**: environment has active users or unarchived data
- **Done when:** destroy plan captured; no active users or unarchived data confirmed

### 2. Approval — `@team-lead` (+ `@product-owner` if production)
- **Input:** destroy plan output from step 1
- Review the destroy plan output
- Confirm: data archived or migrated
- Sign off in the PR/ticket: `APPROVED FOR DESTROY — [name] [date]`
- **Done when:** written approval recorded

### 3. Pre-Destroy Backup — `@devops-engineer`
- **Input:** written approval record from step 2
```bash
# Back up Terraform state file
terraform state pull > backups/state-${ENV}-$(date +%Y%m%d-%H%M%S).tfstate

# If databases present: take final snapshot
pgbackrest --stanza=${ENV}-db --type=full backup

# Export any S3/GCS bucket contents if needed
aws s3 sync s3://${ENV}-data ./backups/s3-${ENV}/
```
- **Done when:** backups verified (not just initiated)

### 4. Ordered Teardown — `@devops-engineer`
- **Input:** verified backups from step 3
```bash
# Destroy in reverse dependency order
# Workloads first, then networking, then storage last

# Option A: full destroy
terraform destroy -var-file=terraform.tfvars -auto-approve

# Option B: targeted destroy (preferred for partial teardown)
# 1. Destroy compute/K8s cluster first
terraform destroy -target=module.k8s_cluster -var-file=terraform.tfvars -auto-approve
# 2. Then networking
terraform destroy -target=module.vpc -var-file=terraform.tfvars -auto-approve
# 3. Finally storage (confirm buckets are empty first)
terraform destroy -target=module.object_storage -var-file=terraform.tfvars -auto-approve
```
- Watch for destroy errors; some resources require manual intervention (e.g., non-empty S3 buckets)
- If destroy fails on a resource: resolve the blocker and re-run the targeted destroy; maximum 3 iterations, then stop and escalate to `@team-lead` with the open blocker list
- **Done when:** all targeted destroys exit 0; no destroy errors outstanding

### 5. Verify & Cleanup — `@devops-engineer`
- **Input:** teardown completion from step 4
```bash
# Confirm no resources remain
terraform state list   # should be empty

# Remove backend state file (only after confirming destroy is complete)
# AWS S3:
aws s3 rm s3://mycompany-terraform-state/${ENV}/ --recursive
# GCS:
gsutil -m rm -r gs://mycompany-terraform-state/${ENV}/

# Remove DynamoDB lock entries
aws dynamodb delete-item \
  --table-name terraform-state-lock \
  --key '{"LockID": {"S": "mycompany-terraform-state/${ENV}/terraform.tfstate"}}'
```
- **Done when:** state list empty; DNS entries removed; cloud console confirms no resources

### 6. Document — `@devops-engineer`
- **Input:** verification results from step 5
- Record in `docs/environments/<env>-decommission.md`: environment, date, approver, reason, data disposition
- **Done when:** decommission record committed to `docs/environments/<env>-decommission.md`

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /destroy-environment"])
  role_1["devops-engineer"]
  role_2["team-lead"]
  role_3["product-owner"]
  step_1["1. Confirm Scope"]
  step_2["2. Approval"]
  step_3["3. Pre-Destroy Backup"]
  step_4["4. Ordered Teardown"]
  step_5["5. Verify & Cleanup"]
  step_6["6. Document"]
  exit(["Terraform state empty + cloud console clean + documentation filed = environ..."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> step_6
  step_6 --> exit
  role_1 -. owns .-> step_1
  role_2 -. owns .-> step_2
  role_3 -. owns .-> step_2
  role_1 -. owns .-> step_3
  role_1 -. owns .-> step_4
  role_1 -. owns .-> step_5
  role_1 -. owns .-> step_6
```
<!-- agent-diagram:end -->

## Exit
Terraform state empty + cloud console clean + documentation filed = environment destroyed.

**Next:** terminal — no follow-up workflow.
