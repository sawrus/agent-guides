---
name: terraform-patterns
description: "Provides Terraform module structure, resource naming, remote state, least-privilege IAM, and anti-pattern guidance; use when writing new Terraform, reviewing IaC PRs, designing module structure, or debugging plan or apply failures."
---

# Skill: Terraform Patterns

## When to load

When writing new Terraform, reviewing IaC PRs, designing module structure, or debugging plan/apply failures.

## Module Structure

```
terraform/
├── modules/
│   ├── vpc/
│   ├── eks-cluster/
│   ├── rds-postgres/
│   └── static-site/
└── environments/
    ├── staging/
    │   ├── main.tf
    │   ├── variables.tf
    │   └── terraform.tfvars
    └── production/
        ├── main.tf
        ├── variables.tf
        └── terraform.tfvars
```

**Rule**: Modules must be generic. Environment-specific values live in `tfvars`, never hardcoded in modules.

## Resource Naming

```hcl
resource "aws_s3_bucket" "this" {
  bucket = "${var.project}-${var.environment}-assets-${random_id.suffix.hex}"
  tags = merge(var.common_tags, { Name = "${var.project}-${var.environment}-assets" })
}
```

## Remote State (Mandatory)

```hcl
terraform {
  backend "s3" {
    bucket         = "my-company-terraform-state"
    key            = "${var.project}/${var.environment}/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    kms_key_id     = "arn:aws:kms:us-east-1:123456789:key/..."
    dynamodb_table = "terraform-state-lock"
  }
}
```

## IAM Least Privilege

```hcl
# ✅ Scoped policy
resource "aws_iam_policy" "app_s3_read" {
  policy = jsonencode({
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject", "s3:ListBucket"]
      Resource = [aws_s3_bucket.assets.arn, "${aws_s3_bucket.assets.arn}/*"]
    }]
  })
}
# ❌ Never: Action = ["s3:*"], Resource = ["*"]
```

## Anti-Patterns

| Anti-pattern | Fix |
|:---|:---|
| `count` for module variants | Use `for_each` with meaningful keys |
| Hardcoded AMI IDs | Use `data "aws_ami"` with filters |
| `terraform_remote_state` across all envs | Use SSM Parameter Store for cross-stack values |
