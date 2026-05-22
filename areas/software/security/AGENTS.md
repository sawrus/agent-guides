# Security — guidance index

## What this area covers

Application and infrastructure security: secure coding standards, dependency auditing, SAST/DAST interpretation, threat modeling, auth patterns, cryptography standards, security headers, secret rotation, and compliance reporting.

## Inherited from general

- Git / CI quality baseline
- SDLC role responsibilities and handoff contracts

## Security-specific constraints

- Security findings with CVSS ≥ 7.0 are release blockers — they are not deferred without explicit documented acceptance by Team Lead and Product Owner.
- Secrets appearing in source code, commits, or logs trigger immediate rotation — no grace period.
- Threat model review is mandatory for features that introduce new data flows, auth boundaries, or external integrations.
- Compliance baseline (`rules/compliance-baseline.md`) applies to every new service by default.

## Spec map

```text
.agent/
├── rules/
│   ├── secure-coding.md          ← OWASP Top 10 mitigations, input validation, output encoding
│   ├── secrets-policy.md         ← storage, rotation, access audit, emergency rotation
│   ├── dependency-policy.md      ← vulnerability SLAs, allowed licenses, patching cadence
│   └── compliance-baseline.md    ← SOC 2 / ISO 27001 controls applicable to all services
├── skills/
│   ├── threat-modeling/SKILL.md          ← STRIDE, DFD construction, mitigations
│   ├── auth-patterns/SKILL.md            ← OAuth2, OIDC, JWT, session management
│   ├── crypto-standards/SKILL.md         ← algorithm selection, key management, TLS config
│   ├── dependency-audit/SKILL.md         ← npm audit, Snyk, OSV, triage workflow
│   ├── sast-dast-interpretation/SKILL.md ← Semgrep, Bandit, OWASP ZAP results triage
│   └── security-headers/SKILL.md         ← CSP, HSTS, CORS, referrer policy
├── workflows/
│   ├── security-scan.md          ← /security-scan
│   ├── threat-model-review.md    ← /threat-model-review
│   ├── secret-rotation.md        ← /secret-rotation
│   ├── pen-test-sim.md           ← /pen-test-sim
│   └── compliance-report.md      ← /compliance-report
└── prompts/
    └── *.md
```
