---
name: ci-cd-pipelines
description: "Provides CI/CD pipeline structure, a GitHub Actions CI template, deployment gates, and an optimization checklist; use when designing GitHub Actions workflows, optimizing pipeline speed, or implementing deployment gates."
---

# Skill: CI/CD Pipeline Patterns

## When to load

When designing GitHub Actions workflows, optimizing pipeline speed, implementing deployment gates.

## Pipeline Structure

```
.github/workflows/
├── ci.yml          # Every PR: lint, test, build, security scan
├── deploy-stg.yml  # Merge to main: deploy to staging
└── deploy-prd.yml  # Release tag: deploy to production (with approval)
```

## CI Template

```yaml
jobs:
  validate:
    steps:
      - uses: actions/cache@v4
        with:
          path: ~/.npm
          key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
      - run: npm ci
      - run: npm run lint && npm run typecheck && npm test -- --coverage

  terraform-validate:
    steps:
      - uses: hashicorp/setup-terraform@v3
      - run: terraform init -backend=false && terraform validate && terraform fmt -check -recursive
        working-directory: terraform/

  security:
    steps:
      - uses: aquasecurity/trivy-action@master
        with: { scan-type: fs, severity: HIGH,CRITICAL, exit-code: 1 }
```

## Deployment Gate

```yaml
jobs:
  deploy:
    environment: production   # Requires reviewer approval in GitHub Environments
    steps:
      - run: kubectl set image deployment/api api=$IMAGE
      - run: npm run test:smoke -- --env production
```

## Pipeline Optimization Checklist

- [ ] Dependencies cached with hash-based keys
- [ ] Independent jobs parallelized (lint + test + security)
- [ ] Docker layer caching enabled
- [ ] Matrix builds for multi-version testing
- [ ] Concurrency groups prevent redundant runs on same branch
