---
name: incident-response
description: "Provides incident severity classification, a P0 response playbook, and common runbooks; use when responding to a production alert, diagnosing an outage, or writing a postmortem."
---

# Skill: Incident Response Runbooks

## When to load

When responding to a production alert, diagnosing an outage, or writing a postmortem.

## Severity Classification

| Severity | Definition | Response Time |
|:---|:---|:---|
| P0 | Complete outage, data loss | Immediate |
| P1 | Significant degradation, key feature broken | 15 min |
| P2 | Minor degradation, workaround exists | 1 hour |
| P3 | Non-user-facing | Next business day |

## P0 Response Playbook

```
T+0:  ACKNOWLEDGE — "I'm on this"
T+5:  SCOPE — What's broken? Who's affected? Since when?
T+10: COMMUNICATE — Post status page update; notify stakeholders
T+15: MITIGATE — Rollback > fix. Prefer reversible actions.
       Order: rollback deploy → feature flag off → scale up → redirect traffic
T+30: STABILIZE — Confirm metrics returning to normal
T+60: DOCUMENT — Write preliminary postmortem
T+24h: POSTMORTEM — Full 5-whys analysis, action items
```

## Common Runbooks

```bash
# High error rate: check recent deploys
kubectl rollout history deployment/api
kubectl logs -l app=api --since=10m | grep ERROR | tail -50
kubectl rollout undo deployment/api  # If recent deploy

# DB connection exhaustion
psql -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"
psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity
         WHERE state = 'idle' AND age(clock_timestamp(), state_change) > interval '10 minutes';"
```
