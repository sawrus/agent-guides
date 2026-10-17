---
name: sast-dast-interpretation
description: "Interprets SAST and DAST results with a triage matrix, common false positives, and OWASP ZAP priority findings; use when reviewing security scan results, triaging vulnerabilities, or deciding which findings to fix or accept."
---

# Skill: SAST/DAST Results Interpretation

## When to load

When reviewing security scan results, triaging vulnerabilities, or deciding which findings to fix vs. accept.

## SAST Triage Matrix

| Severity | CVSS | Action | Timeline |
|:---|:---|:---|:---|
| Critical | 9.0–10.0 | Block merge, fix immediately | Same day |
| High | 7.0–8.9 | Block deploy | 72 hours |
| Medium | 4.0–6.9 | Track as tech debt | 2 weeks |
| Low | 0.1–3.9 | Backlog | Next quarter |

## Common False Positives

```
False positive: "SQL Injection" on ORM query
→ Verify ORM parameterizes internally → add suppression comment:
// snyk:ignore:sql-injection -- parameterized ORM query

False positive: "Hardcoded credential" on config key name
→ Verify value comes from env var → suppress with justification
```

## OWASP ZAP Priority Findings

1. Missing security headers (CSP, X-Frame-Options) → always exploitable, easy fix
2. Information disclosure in error responses → check stack traces
3. CSRF → verify token on all state-changing requests
4. Clickjacking → add `frame-ancestors` CSP directive
5. Insecure cookies → verify Secure, HttpOnly, SameSite=Strict/Lax
