---
description: Signing, provenance, SBOM, and pinning requirements for artifacts that a pipeline builds and deploys.
paths:
  - ".gitlab-ci.yml"
  - "**/.gitlab-ci.yml"
  - ".gitlab/**"
  - ".github/workflows/**"
  - "**/Dockerfile"
  - "**/Containerfile"
---

# Supply chain security

- Sign every release image keylessly with `cosign sign --yes <image>@sha256:<digest>` from the CI job identity.
- Verify signatures in the deploy job with `cosign verify --certificate-oidc-issuer` and `--certificate-identity-regexp` bound to the repository and release refs.
- Keep signing keys in a KMS or HSM and rotate them at least every 90 days when keyless signing is not available.
- Generate an SLSA provenance attestation for every production build and bind it to the commit SHA.
- Generate a CycloneDX or SPDX SBOM for the exact image digest and store it with the artifact.
- Deploy images by `@sha256` digest only; never reference `latest` or another mutable tag in a manifest.
- Pin base images in every `Dockerfile` by `@sha256` digest.
- Commit lockfiles (`package-lock.json`, `poetry.lock`, `uv.lock`, `go.sum`, `gradle.lockfile`) for every direct dependency set.
- Enable checksum verification of the package manager (`npm ci`, `pip install --require-hashes`, `GOFLAGS=-mod=readonly`).
- Pin CI includes, actions, and plugins to an immutable commit SHA or tag `ref:`.
- Fail the deploy job when signature, provenance, or SBOM verification fails or the verifier is unreachable.
- Limit a policy exception to 14 days and record its owner and expiry date in the policy file.
- Keep commit SHA, SBOM digest, provenance digest, signer identity, and scan results for each release for at least 1 year.
