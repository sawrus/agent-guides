---
description: Admission policies (Kyverno or OPA Gatekeeper) that every cluster enforces, and how to test them.
paths:
  - "**/policies/**"
  - "**/kyverno/**"
  - "**/gatekeeper/**"
  - "**/*.rego"
---

# Policy as code

- Keep admission policies in the repository under `policies/`; do not create policies by hand in a cluster.
- Enforce these policies in every cluster: `disallow-privileged-containers`, `require-non-root-user`, `require-resource-limits`, `require-image-digest`, `disallow-host-namespaces`.
- Set `require-readonly-root-filesystem` to `Audit` in staging and `Enforce` in production.
- Require verified image signatures (`verifyImages` in Kyverno or an equivalent constraint) in production namespaces.
- Use Kyverno YAML policies for single-resource checks; use OPA Rego only when a policy needs cross-resource data.
- Add a test case for each policy: `kyverno test .` with pass and fail resources, or `opa test policies/ -v` for Rego.
- Run the policy tests in CI and fail the pipeline on any failed test case.
- Roll out a new policy with `validationFailureAction: Audit` first and switch to `Enforce` after the audit report shows no violations.
- Limit a `PolicyException` to named resources and set an expiry date annotation on it.
