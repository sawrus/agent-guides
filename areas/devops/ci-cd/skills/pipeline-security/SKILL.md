---
name: pipeline-security
type: skill
description: Secure CI/CD pipelines with keyless signing, OIDC federation, provenance attestations, policy enforcement, and hardened runners.
related-rules:
  - supply-chain-security.md
  - pipeline-standards.md
allowed-tools: Read, Write, Edit
---

# Skill: Pipeline Security

> **Expertise:** OIDC cloud auth, least-privilege workflow permissions, secret scanning, keyless artifact signing, SLSA provenance, and admission policy checks.

## When to load

When designing or hardening CI/CD pipelines for production deployments, especially where compliance or high-risk workloads are involved.

## Security Outcomes (definition of done)

- Pipeline uses **OIDC federation** (no long-lived cloud keys in CI secrets).
- Artifacts are **signed keylessly** and verified with identity constraints.
- **Provenance + SBOM** are generated and validated before deploy.
- Workflows use **minimal GitHub/GitLab permissions**.
- Runtime admission policies block unsigned/unattested artifacts.

## OIDC Authentication (no long-lived credentials)

```yaml
jobs:
  deploy:
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: aws-actions/configure-aws-credentials@<pinned-sha>
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-deploy
          aws-region: us-east-1
```

- Constrain trust policy by repo, ref, and workflow identity.
- Prefer short session duration and environment-scoped roles.

## Minimal Permissions Model

```yaml
permissions:
  contents: read
  id-token: write
  packages: write
```

- Deny by default; explicitly request only required scopes.
- Split build and deploy into separate jobs with separate permissions.

## Keyless Signing + Verification

```bash
# Sign immutable artifact digest
cosign sign --yes registry.example.com/team/service@sha256:<digest>

# Verify identity and issuer in deploy gate
cosign verify \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  --certificate-identity-regexp 'https://github.com/myorg/myrepo/\.github/workflows/.+@refs/tags/v.+' \
  registry.example.com/team/service@sha256:<digest>
```

## Provenance + SBOM Requirements

- Generate SLSA provenance attestation for each release artifact.
- Generate CycloneDX/SPDX SBOM for exact artifact digest.
- Store attestation/SBOM references in release metadata.
- Block deploy if attestation/SBOM is missing or invalid.

## Secret and Dependency Controls

- Run secret scanning (trufflehog/gitleaks) on PR and main.
- Run dependency review with severity threshold and license policy.
- Fail pipeline on critical policy violations; do not “warn-only” for production paths.

## Runner Hardening

- Ephemeral runners preferred (one job per VM/pod).
- No privileged mode unless explicitly justified.
- Restrict network egress to required registries/APIs.
- Never persist cloud credentials or kubeconfig on runner disk.

## Policy-as-Code Integration

- Enforce cluster admission checks for:
  - signed image;
  - digest-only reference;
  - valid provenance for production namespaces.
- Keep exception path explicit: owner + expiry + compensating controls.
