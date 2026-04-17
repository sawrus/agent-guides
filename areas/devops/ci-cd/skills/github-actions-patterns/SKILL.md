---
name: github-actions-patterns
type: skill
description: "Production-grade GitHub Actions workflows — reusable workflows, OIDC cloud auth, caching, matrix builds, and environment protection rules. Use when the user creates, reviews, or debugs CI/CD pipelines in .github/workflows, or asks about GitHub Actions deployment, OIDC authentication, or workflow optimization."
related-rules:
  - pipeline-standards.md
  - quality-gates.md
  - supply-chain-security.md
allowed-tools: Read, Write, Edit
---

# Skill: GitHub Actions Patterns

> **Expertise:** Reusable workflows, composite actions, OIDC cloud auth, build caching, deployment gates, self-hosted runners.

## When to load

When creating or reviewing GitHub Actions workflows for CI, CD, or infrastructure automation.

## Standard CI Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true   # cancel outdated runs on new push

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip               # built-in pip caching

      - name: Install deps
        run: pip install -r requirements.txt -r requirements-dev.txt

      - name: Lint
        run: ruff check src/ tests/

      - name: Type check
        run: mypy src/ --strict

      - name: Test with coverage
        run: |
          pytest tests/ \
            --cov=src \
            --cov-report=xml \
            --cov-fail-under=80

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml

  build:
    needs: validate
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      id-token: write            # for OIDC
    outputs:
      image-digest: ${{ steps.build.outputs.digest }}
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to registry (OIDC — no long-lived secret)
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        id: build
        uses: docker/build-push-action@v6
        with:
          context: .
          push: ${{ github.event_name == 'push' }}
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          provenance: true         # SLSA provenance attestation
          sbom: true               # generate SBOM

  security-scan:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Scan image for CVEs
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ghcr.io/${{ github.repository }}:${{ github.sha }}
          format: sarif
          output: trivy-results.sarif
          severity: CRITICAL,HIGH
          exit-code: 1            # fail pipeline on Critical/High

      - name: Upload SARIF to Security tab
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: trivy-results.sarif
```

## Reusable Workflow Pattern

```yaml
# .github/workflows/_deploy.yml (reusable — called by others)
name: Deploy (reusable)

on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
      image-digest:
        required: true
        type: string
    secrets:
      KUBECONFIG_B64:
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}   # GitHub Environment with protection rules
    steps:
      - name: Deploy via Helm
        env:
          KUBECONFIG_B64: ${{ secrets.KUBECONFIG_B64 }}
        run: |
          echo "$KUBECONFIG_B64" | base64 -d > /tmp/kubeconfig
          helm upgrade --install my-service charts/my-service \
            --set image.digest=${{ inputs.image-digest }} \
            --namespace ${{ inputs.environment }} \
            --atomic --timeout 5m

      - name: Verify deployment health
        run: |
          kubectl rollout status deployment/my-service -n ${{ inputs.environment }} --timeout=120s
          curl -sf http://my-service.${{ inputs.environment }}.svc.cluster.local/health || exit 1
```

## OIDC Cloud Authentication (no long-lived keys)

```yaml
# AWS via OIDC (no AWS_ACCESS_KEY_ID needed)
- name: Configure AWS credentials
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789:role/github-actions-deploy
    aws-region: us-east-1

# GCP via OIDC
- name: Authenticate to Google Cloud
  uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: projects/123/locations/global/workloadIdentityPools/...
    service_account: github-actions@my-project.iam.gserviceaccount.com
```

## Self-Hosted Runner (bare-metal K8s)

```yaml
# Use self-hosted runner for internal registry / VPN-required builds
jobs:
  build-internal:
    runs-on: [self-hosted, linux, k8s-runner]
    steps:
      - ...
```

## Environment Protection Rules

Configure in GitHub → Settings → Environments:
- `production`: require manual approval from `@devops-team` + `@team-lead`; restrict to `main` branch only
- `staging`: auto-deploy; restrict to `main` branch
