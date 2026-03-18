---
name: module-development
type: workflow
trigger: /module-develop
description: Develop, test, and publish a new reusable Terraform module — design, implementation, examples, tests, and versioned release.
inputs:
  - module_name
  - module_purpose
  - cloud_targets
outputs:
  - published_module
  - module_documentation
roles:
  - devops-engineer
  - team-lead
execution:
  initiator: developer
related-rules:
  - iac-standards.md
  - state-management.md
uses-skills:
  - terraform-modules
  - drift-detection
quality-gates:
  - all examples produce clean plan (no-op on re-apply)
  - terraform validate passes
  - no provider config inside module
  - README documents all variables and outputs
---

## Steps

### 1. Design Interface — `@devops-engineer` + `@team-lead`
- Define: what problem does this module solve?
- Map all input variables (required vs optional with defaults)
- Map all outputs callers will need
- Decide: cloud-specific or cloud-agnostic? (prefer agnostic with per-cloud examples)
- **Done when:** interface design reviewed and signed off

### 2. Implement Module — `@devops-engineer`
```
modules/<module-name>/
├── main.tf         ← resource definitions
├── variables.tf    ← all inputs with descriptions + validation
├── outputs.tf      ← all outputs with descriptions
├── versions.tf     ← required_version + required_providers (no provider block)
└── README.md       ← auto-generated with terraform-docs
```
- Add `validation {}` blocks to all critical variables
- Use `for_each` over `count` for multi-instance resources
- No hardcoded regions, account IDs, or environment names
- **Done when:** `terraform validate` passes; `terraform fmt -check` passes

### 3. Write Examples — `@devops-engineer`
```
modules/<module-name>/examples/
├── basic/          ← minimal config, happy path
│   ├── main.tf
│   └── README.md
└── advanced/       ← all options exercised
    ├── main.tf
    └── README.md
```
- Examples must have complete provider configs
- Run each example against a test account/project: `terraform init && terraform plan`
- **Done when:** both examples produce a clean plan

### 4. Test — `@devops-engineer`
```bash
# Terratest (Go)
cd modules/<module-name>/test
go test -v -timeout 30m

# Or: checkov for static security analysis
checkov -d modules/<module-name>/ --quiet

# terraform-docs: generate README from code
terraform-docs markdown table modules/<module-name>/ \
  > modules/<module-name>/README.md
```

### 5. Code Review — `@team-lead`
- Interface is minimal (no unnecessary variables)
- No provider config in module
- Examples clean
- README complete (all variables, outputs, usage examples)
- **Done when:** PR approved

### 6. Release — `@devops-engineer`
```bash
# Semantic version tag
git tag -a modules/<module-name>/v1.0.0 \
  -m "Initial release of <module-name> module"
git push origin modules/<module-name>/v1.0.0

# Update module registry / internal docs
# Reference in other modules: ?ref=v1.0.0 (never ?ref=main)
```

## Exit
Module published + examples tested + documentation complete = module released.
