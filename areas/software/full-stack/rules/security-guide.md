---
trigger: model_decision
glob: security-guide
description: enforce cloud-native security controls: authZ, secure service identity, secrets lifecycle, and high-risk input protections
---

# Security Rule

**Priority**: P0 — Security regressions in authentication, authorization, data protection, or high-risk input handling block release.

## Mandatory Controls

1. **AuthN/AuthZ baseline**
   - Default-deny authorization at route and resource level.
   - Enforce object-level access checks (prevent IDOR/BOLA).
   - Short-lived tokens with rotation and revocation strategy.

2. **Service-to-service identity**
   - Use workload identity / mTLS where possible.
   - No long-lived static credentials between services.
   - Scope service permissions to least privilege.

3. **Input and output hardening**
   - Validate all external input with strict schema and type constraints.
   - Prevent mass assignment via explicit allowlists of writable fields.
   - Apply output encoding/sanitization where user-generated content is rendered.

4. **High-risk attack classes to address explicitly**
   - SSRF protections (deny internal metadata ranges, allowlist outbound domains).
   - Insecure deserialization prevention (safe parsers, signed payloads where needed).
   - Unsafe file upload controls (MIME + extension + antivirus + storage isolation).

5. **Secrets lifecycle**
   - Secrets stored only in secret manager/vault.
   - Rotation cadence defined per secret class.
   - Emergency revocation runbook required.

6. **Data and transport protection**
   - Encrypt in transit (TLS 1.2+ minimum) and at rest.
   - Avoid logging secrets, tokens, or sensitive PII.

7. **Auditability**
   - Security-relevant actions (auth, privilege changes, key operations) must be audit logged.
   - Logs should be tamper-evident and correlated with request/user/service identity.

## Release Security Checklist (required)

- Threat model updated for new trust boundaries/data flows.
- AuthZ checks validated by tests on critical endpoints.
- Secret exposure checks run in CI and deployment logs.
- Dependency risks triaged with exploitability status.

## Violations

- Hardcoded secrets or tokens in code/config.
- Missing object-level authorization.
- Unvalidated/deserialized untrusted payloads.
- Service credentials shared across environments without isolation.
