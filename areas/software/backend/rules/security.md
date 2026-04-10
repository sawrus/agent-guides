# Rule: Backend Security & OWASP Standards

**Priority**: P0 — Security vulnerabilities affecting confidentiality, integrity, or availability are release blockers.

## OWASP-aligned baseline

1. **Access control and authorization**
   - Default-deny endpoint access.
   - Enforce RBAC/ABAC and object-level authorization for every resource operation.
   - Test negative authorization paths (forbidden cross-tenant access).

2. **Authentication and session/token lifecycle**
   - Validate issuer, audience, expiry, and signature for tokens.
   - Use short-lived access tokens and revocable refresh strategy.
   - Detect and alert on anomalous auth patterns.

3. **Cryptography and secrets**
   - Use modern algorithms (Argon2id/bcrypt for password hashing).
   - Secrets only from dedicated manager (Vault/AWS/GCP/Azure secret stores).
   - Define key/secret rotation and emergency revocation procedures.

4. **Injection and input safety**
   - Parameterized queries only; no string-concatenated SQL.
   - Strict DTO/schema validation at boundaries.
   - Block mass assignment with explicit writable-field allowlists.

5. **Critical web attack defenses**
   - SSRF protections for outbound HTTP integrations.
   - Safe deserialization only; reject untrusted executable payload formats.
   - File upload protection: type validation, scanning, quarantine storage.

6. **Service identity and least privilege**
   - Prefer workload identity/mTLS for service-to-service auth.
   - Avoid static credentials in runtime environments.
   - Separate service accounts per environment and per bounded context.

7. **Security telemetry and audit**
   - Log auth events, privilege changes, and sensitive config access.
   - Mask/redact sensitive fields in logs and traces.
   - Propagate correlation IDs for incident reconstruction.
