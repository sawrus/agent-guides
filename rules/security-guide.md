---
trigger: model_decision
glob: security-guide
description: enforce secrets handling, input validation, and least privilege
---

# Security Rule

**Rules:**

- Never hardcode secrets or credentials.
- Validate all external input (API, DB, files).
- Use Bearer Auth in headers.
- Apply the least privilege for DB, API, files.
- Encrypt sensitive data in transit and at rest.
- Audit and sanitize logs to avoid secrets leakage.

**Violations:**

- Raw secrets in code.
- Unvalidated user input.
- Elevated privileges without justification.
