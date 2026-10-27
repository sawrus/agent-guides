---
description: No in-place changes to running infrastructure, drift checks, and the emergency change path.
paths:
  - "**/*.tf"
  - "**/*.tfvars"
  - "**/packer/**"
  - "**/*.pkr.hcl"
---

# Immutable infrastructure

- Fix a running server with a new image and a redeploy; never patch it over SSH or in the cloud console.
- Change production resources only through Terraform code; do not use the console, CLI, or SDK for them.
- Build machine images with Packer (`*.pkr.hcl`) and reference them by image ID or digest, not by a `latest` name filter.
- Use `create_before_destroy = true` for resources that serve traffic during replacement.
- Run a scheduled drift check (`terraform plan -detailed-exitcode`) at least every 6 hours for each production state.
- Tag each drift finding `accept`, `remediate`, or `investigate`; fix a `remediate` finding within 48 hours.
- Create a P1 incident for drift of unknown origin and for any drift in security groups or IAM `policy` resources.
- Allow a manual production change only during a P0 incident and merge the matching IaC change within 24 hours.
