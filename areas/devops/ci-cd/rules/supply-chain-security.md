# Rule: Supply Chain Security

**Priority**: P0 — Artifacts without verified identity, provenance, and policy compliance are blocked from production.

## Baseline (mandatory)

1. **Keyless signing by default**: use Sigstore keyless (`cosign` + OIDC/Fulcio/Rekor) for CI-produced artifacts.
2. **Immutable references only**: deploy by digest (`@sha256:...`), never mutable tags (`latest`, `stable`).
3. **Provenance required**: generate SLSA-compatible provenance attestations for every production build.
4. **SBOM required**: generate CycloneDX or SPDX SBOM and attach/store with the exact artifact digest.
5. **Admission policy enforcement**: clusters must verify signature + provenance + digest pinning before workload admission.

## Signing and Verification

```bash
# Keyless signing (preferred)
cosign sign --yes registry.example.com/my-service@sha256:<digest>

# Verification with issuer/identity constraints (required in CD)
cosign verify \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  --certificate-identity-regexp 'https://github.com/myorg/myrepo/\.github/workflows/.+@refs/tags/v.+' \
  registry.example.com/my-service@sha256:<digest>
```

6. **Key-pair signing is fallback only**: if keyless is unavailable, keys must be in KMS/HSM and rotated at least quarterly.
7. **Transparency log evidence**: verification must include Rekor entry checks when supported.

## Provenance and Build Integrity

8. Production builds run only on trusted CI and produce attestations bound to exact commit SHA.
9. Build provenance must include: repository, workflow identity, source revision, build parameters, and builder identity.
10. Reproducibility target: deterministic builds for critical services; if not feasible, document non-deterministic inputs.

## Dependency and Base Image Controls

11. Pin direct dependencies and commit lockfiles (`package-lock.json`, `poetry.lock`, `go.sum`, etc.).
12. Base images pinned by digest in Dockerfile; floating tags are forbidden.
13. Package managers must verify checksums/hashes where available.
14. External CI actions/plugins must be pinned to immutable commit SHA.

## Policy Enforcement (Kubernetes / CD)

15. Admission controllers (Kyverno/Gatekeeper) must enforce:
   - signed image verification;
   - digest-only image references;
   - required provenance attestation for production namespaces.
16. Deploy pipeline fails closed if verification services are unavailable (no silent bypass).
17. Exceptions require documented risk acceptance with owner + expiry date (max 14 days).

## Audit Trail and Retention

18. Keep artifact metadata for at least 1 year: commit SHA, SBOM digest, provenance digest, signer identity, scan results.
19. Every release record must be traceable from ticket/PR → commit → artifact digest → deployment event.
