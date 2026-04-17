---
name: threat-modeling
type: skill
description: "Apply STRIDE threat modeling to system designs, identify IDOR and authorization vulnerabilities, and build threat matrices for security reviews. Use when the user designs a new system, reviews an architecture, prepares for a security audit, or asks about common API vulnerabilities like IDOR or broken access control."
related-rules:
  - security-baseline.md
allowed-tools: Read, Bash
---

# Skill: Threat Modeling

> **Expertise:** STRIDE framework, IDOR prevention, authorization boundary analysis, threat matrices for API and system security reviews.

## When to load

When designing a new system, adding an integration, reviewing an architecture, or preparing for a security review.

## STRIDE Framework

| Threat | Question | Example |
|:---|:---|:---|
| **S**poofing | Can an attacker impersonate a user/service? | Forged JWT, SSRF to metadata service |
| **T**ampering | Can data be modified in transit/at rest? | SQL injection, cache poisoning |
| **R**epudiation | Can users deny performing an action? | Missing audit logs |
| **I**nformation Disclosure | Can sensitive data be exposed? | Error messages leaking stack traces |
| **D**enial of Service | Can the service be made unavailable? | No rate limiting on public endpoints |
| **E**levation of Privilege | Can a low-privilege user gain higher access? | IDOR, broken object-level authorization |

## Threat Modeling Workflow

1. **Identify assets** — list sensitive data, APIs, and trust boundaries in the system
2. **Apply STRIDE** — walk through each threat category against every asset and boundary
3. **Score risks** — rank by likelihood × impact (Critical / High / Medium / Low)
4. **Prioritize mitigations** — address Critical/High first; document accepted risks for Medium/Low
5. **Validate** — verify mitigations with code review, SAST/DAST scans, or penetration testing

## IDOR — Most Common API Vulnerability

```python
# ❌ Vulnerable
@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: int, current_user: User = Depends(get_current_user)):
    return db.query(Invoice).filter(Invoice.id == invoice_id).first()

# ✅ Safe: always scope to authenticated user
@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: int, current_user: User = Depends(get_current_user)):
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.owner_id == current_user.id  # ← ownership check
    ).first()
    if not invoice:
        raise HTTPException(status_code=404)  # 404, not 403
    return invoice
```

## Common Mistakes

- **Returning 403 instead of 404** — reveals that the resource exists, enabling enumeration
- **Client-side authorization only** — always enforce ownership and role checks server-side
- **Missing audit logs for sensitive actions** — makes repudiation threats undetectable
- **Trusting internal service-to-service calls** — apply zero-trust; validate JWTs at every boundary
