---
name: sbom-supply-chain
description: "Procedure to generate an SBOM, scan it for vulnerabilities, and sign and verify container images and attestations with cosign. Use when you add SBOM, image signing, or provenance to a pipeline or verify an image."
---

# SBOM, scanning, and signing

## 1. Generate the SBOM from the built image

Build the image once and refer to it by digest in every later step.

```bash
IMAGE=registry.example.com/group/service@sha256:<digest>
syft "$IMAGE" -o cyclonedx-json > sbom.cdx.json
```

- Use the image, not the source tree, so the SBOM lists what ships.
- Keep `sbom.cdx.json` as a pipeline artifact (`artifacts:` in GitLab, `actions/upload-artifact` in GitHub).

## 2. Scan the SBOM

```bash
grype sbom:sbom.cdx.json --fail-on high
trivy sbom sbom.cdx.json --severity HIGH,CRITICAL --exit-code 1
```

1. If a finding has a fixed version, upgrade the package or the base image and rebuild.
2. If there is no fix, decide with the user: accept with an expiry date in the ignore file
   (`.grype.yaml` or `.trivyignore`) and a reason comment, or block the release.
3. Do not raise `--fail-on` to make the job pass.

## 3. Sign the image

Prefer keyless signing with the pipeline OIDC identity.

- GitLab: add `id_tokens: SIGSTORE_ID_TOKEN: aud: sigstore` to the job.
- GitHub: set `permissions: id-token: write`.

```bash
cosign sign --yes "$IMAGE"
cosign attest --yes --type cyclonedx --predicate sbom.cdx.json "$IMAGE"
```

If the project uses a key pair, read it from a KMS (`--key gcpkms://...`, `awskms://...`, `hashivault://...`).
Never commit `cosign.key`.

## 4. Verify before deploy

```bash
cosign verify "$IMAGE" \
  --certificate-identity-regexp '^https://gitlab.example.com/group/service//' \
  --certificate-oidc-issuer https://gitlab.example.com
cosign verify-attestation --type cyclonedx "$IMAGE" ...same identity flags...
```

1. Add the verify step to the deploy job, before the deploy command.
2. In Kubernetes, enforce the same identity with an admission policy (Kyverno `verifyImages` or Sigstore
   policy-controller). Ask the user first before you enable enforcement on a production cluster.

## 5. Done

- The pipeline produces the SBOM, fails on high and critical findings, and signs the image by digest.
- The deploy job verifies the signature and stops on a failed verification.
