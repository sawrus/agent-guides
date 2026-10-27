---
description: Authentication, authorization, input validation, and secret handling in backend service code.
paths:
  - "**/*.py"
  - "**/*.go"
  - "**/*.java"
  - "**/*.kt"
---

# Backend security

- Deny by default: every endpoint has an explicit authentication requirement and authorization check.
- Check object-level authorization (owner or tenant) for every read and write by id; add a test for cross-tenant access that expects `403` or `404`.
- Validate tokens for signature, `iss`, `aud`, `exp`, and `nbf`; reject `alg: none` and unexpected algorithms.
- Keep access token lifetime at 15 minutes or less; store refresh tokens server-side so they can be revoked.
- Hash passwords with Argon2id or bcrypt; never use MD5, SHA-1, or unsalted SHA-256 for passwords.
- Validate every request body against a schema (Pydantic, Bean Validation, struct tags) with unknown fields rejected.
- Use an allowlist of writable fields; never bind a request body directly to an ORM entity (mass assignment).
- Read secrets from environment variables or a secret manager at startup; never commit a secret or default it in code.
- Restrict outbound HTTP to an allowlist of hosts when the URL comes from user input (SSRF).
- Do not deserialize untrusted data with `pickle`, Java native serialization, or YAML `load` without a safe loader.
- Check type and size of uploaded files and store them outside the web root.
- Log authentication failures, permission changes, and admin actions with the user id and request id.
- Never log passwords, tokens, full card numbers, or session cookies; mask them in logs and traces.
- Use a separate service account per service and per environment; no shared credentials.
