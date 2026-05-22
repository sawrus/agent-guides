# DevSecOps — guidance index

## What this area covers

Shift-left security integration: container hardening, SBOM and supply-chain attestation, OPA / Kyverno policy enforcement, secret detection, and Sigstore artifact signing. Security controls are embedded in the delivery pipeline, not applied after the fact.

## Guidance chain

1. Project `.agent/` baseline
2. `.agent/rules/*` — load all
3. `.agent/skills/*/SKILL.md` — load only the skill matching the current task
4. `.agent/workflows/*` — load the workflow matching the triggered command

## Cross-cutting constraints

- **Shift left** — security checks run in CI, not in a post-deploy audit.
- **Policy as code** — all security policies are version-controlled and machine-enforced; manual review is a supplement, not a substitute.
- **Container images are immutable artifacts** — no shell access, no package installs at runtime.
- **Every artifact is signed** — unsigned images and binaries are rejected at admission.

## Spec map

```text
.agent/
├── rules/
│   ├── shift-left-policy.md       ← required CI checks, fail-fast thresholds
│   ├── container-security.md      ← base image standards, rootless, read-only FS
│   └── policy-as-code.md          ← OPA/Kyverno enforcement points, violation handling
├── skills/
│   ├── container-hardening/SKILL.md    ← distroless, non-root, capability drops
│   ├── sbom-supply-chain/SKILL.md      ← Syft, CycloneDX, SLSA provenance
│   ├── opa-policies/SKILL.md           ← Rego authoring, Conftest, Gatekeeper
│   ├── secret-detection/SKILL.md       ← Gitleaks, truffleHog, pre-commit integration
│   └── sigstore-signing/SKILL.md       ← Cosign, keyless signing, Rekor transparency log
├── workflows/
│   ├── security-scan-pipeline.md   ← /security-scan-pipeline
│   └── policy-onboard.md           ← /policy-onboard
└── prompts/
    └── *.md
```

## Discovery patterns

- `.agent/rules/*.md`
- `.agent/skills/*/SKILL.md`
- `.agent/workflows/*.md`
- `.agent/prompts/*.md`
