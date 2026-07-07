---
name: onboard-repo
type: workflow
trigger: /onboard-repo
description: Set up CI/CD pipeline for a new repository — from zero to production-grade pipeline with quality gates and deployment automation.
inputs:
  - repo_name
  - language/framework
  - ci_platform (github-actions|gitlab-ci)
  - deploy_target (kubernetes|vm)
outputs:
  - pipeline_config
  - first_successful_run
roles:
  - devops-engineer
  - developer
execution:
  initiator: developer
related-rules:
  - pipeline-standards.md
  - quality-gates.md
  - supply-chain-security.md
uses-skills:
  - github-actions-patterns
  - gitlab-ci-patterns
  - pipeline-security
quality-gates:
  - pipeline runs green on first PR
  - all mandatory stages present
  - no hardcoded secrets in pipeline config
---

## Steps

### 1. Assess & Plan — `@devops-engineer`
- **Input:** repo_name, language/framework, ci_platform, and deploy_target from the workflow inputs.
- **Actions:**
  - Confirm language, build tool, test framework
  - Identify external dependencies (registry, cloud, K8s cluster)
  - Choose CI platform (GitHub Actions vs GitLab CI) based on repo location
  - Identify secrets needed: registry creds, kubeconfig, cloud role
- **Output:** pipeline design doc (stages, auth method, environments)
- **Done when:** design approved by developer and team-lead

### 2. Secrets & Environments Setup — `@devops-engineer`
- **Input:** approved pipeline design doc from step 1.
- **Actions:**
  - Create OIDC cloud role (preferred) or minimal-privilege service account
  - Configure CI secrets: registry login, kubeconfig (base64), vault token
  - Create environment definitions (staging, production) with protection rules
- **Done when:** secrets configured; OIDC trust policy in place

### 3. Write Pipeline Config — `@devops-engineer`
- **Input:** configured secrets and environment definitions from step 2.
- **Actions:**
  - Create `.github/workflows/ci.yml` or `.gitlab-ci.yml`
  - Implement all mandatory stages (lint → test → build → scan → deploy)
  - Add caching for dependencies (pip/npm/go modules)
  - Add image signing (cosign) and SBOM generation
  - Configure coverage reporting and test result upload
- **Output:** pipeline config committed to feature branch
- **Done when:** `yamllint` passes; no syntax errors

### 4. First Run & Debug — `@devops-engineer` + `@developer`
- **Input:** pipeline config committed to the feature branch in step 3.
- **Actions:**
  - Open PR to trigger pipeline
  - Fix any failing stages (missing deps, wrong paths, auth issues)
  - Verify each stage output matches expectations
- **Done when:** all stages green on PR; deployment to staging succeeds

### 5. Document — `@devops-engineer`
- **Input:** green pipeline and staging deployment from step 4.
- Write `docs/ci-cd.md`: stages, how to run locally, how to add a new secret
- **Done when:** documentation committed

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /onboard-repo"])
  role_1["devops-engineer"]
  role_2["developer"]
  step_1["1. Assess & Plan"]
  step_2["2. Secrets & Environments Setup"]
  step_3["3. Write Pipeline Config"]
  step_4["4. First Run & Debug"]
  step_5["5. Document"]
  exit(["Green pipeline + staging deploy + documentation = repo onboarded."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> exit
  role_1 -. owns .-> step_1
  role_1 -. owns .-> step_2
  role_1 -. owns .-> step_3
  role_1 -. owns .-> step_4
  role_2 -. owns .-> step_4
  role_1 -. owns .-> step_5
```
<!-- agent-diagram:end -->

## Exit
Green pipeline + staging deploy + documentation = repo onboarded.

**Next:** terminal — no follow-up workflow.
