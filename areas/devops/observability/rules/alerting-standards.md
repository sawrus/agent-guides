# Rule: Alerting Standards

**Priority**: P1 — Alerts must be actionable, SLO-aligned, and mapped to ownership.

## Alert Quality Rules

1. **Runbook required** — every alert includes `runbook_url` and service owner.
2. **Actionability required** — alerts without a defined human or automated action are downgraded to dashboard signals.
3. **Symptom-first** — page on user impact, not raw infrastructure noise.

## Severity Model

| Severity | Meaning | Response |
|:---|:---|:---|
| `critical` | Active user-impacting incident / fast error-budget burn | Page on-call immediately |
| `warning` | Degradation trending toward SLO breach | Notify team channel, triage in business hours or sooner |
| `info` | Context signal only | Dashboard or ticket, no paging |

## Multi-Window Burn-Rate Standard

4. Define at least:
   - **fast burn** alert (e.g., ~1h window),
   - **slow burn** alert (e.g., ~6h window).
5. Fast burn pages on-call; slow burn creates prioritized reliability action.
6. Burn-rate thresholds must map to error-budget policy and release gating.

## Anti-Fatigue and Signal Hygiene

7. Configure `for:` durations to reduce noise.
8. If an alert fires repeatedly without action, either improve runbook/automation or retire the alert.
9. Track alert precision/recall metrics during reliability reviews.

## Routing and Escalation

10. Route by service ownership and environment (prod vs non-prod).
11. Define escalation path and timeout for unacknowledged critical alerts.
12. Support maintenance windows and silence policies with audit logging.

## Auto-Remediation

13. For known-safe remediations (e.g., restart stateless worker), allow guarded auto-remediation.
14. Auto-remediation actions must emit events and be reversible.
