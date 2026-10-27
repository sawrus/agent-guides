---
description: Incident severities, response times, runbooks, access, and toil limits for on-call rotations.
trigger: manual
---

# On-call standards

- Use the severities P0 (full outage or data loss), P1 (major feature broken or over 25 % of users affected), P2 (degraded with a workaround), and P3 (no user impact).
- Acknowledge P0 pages within 5 minutes, P1 within 15 minutes, and P2 within 1 hour in business hours.
- Limit each engineer to 1 primary and 1 secondary on-call week per month.
- Link a runbook from every alert that can page; set an alert without a runbook to `warning` until the runbook exists.
- Store runbooks in the repository next to the alert rules or in `docs/runbooks/`.
- Give on-call engineers read access to production and write access limited to rollback, scale, and restart; require a separate MFA step for wider access.
- Document the escalation path in the paging tool and test it every quarter.
- Log every manual production action during an incident in the incident channel with a timestamp.
- Track toil hours per rotation; start automation work when toil exceeds 50 % of on-call time for 2 rotations in a row.
