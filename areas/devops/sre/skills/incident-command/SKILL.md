---
name: incident-command
description: "Procedure to run a production incident: declare and set severity, gather evidence, mitigate before root cause, keep a timeline, communicate, and hand off. Use when a service is down or degraded or an alert pages."
---

# Incident command

Mitigate first, find the root cause later. Every action on production needs the user's go-ahead.

## 1. Declare

1. State the symptom in one sentence: what fails, for whom, since when.
2. Set the severity from the project on-call rule (`on-call-standards.md` when the sre spec is installed):

| Severity | Condition |
|---|---|
| P0 | Full outage, data loss, or security breach |
| P1 | Major feature broken or over 25 % of users affected |
| P2 | Degraded with a workaround |
| P3 | No user impact yet |

3. Start a timeline with UTC times. Add every action and finding as one line.

## 2. Gather evidence (read-only)

1. Alerts and dashboards: error rate, latency, saturation of the service and its dependencies.
2. Recent changes: last deploys (`git log --since=<time>`, `kubectl rollout history`, pipeline history),
   feature flags, config changes, infrastructure changes.
3. Logs around the start time: filter by the error and by request id.
4. Dependencies: database, queue, external APIs, DNS, certificates (`openssl s_client -connect <host>:443`).
5. Write the leading hypothesis and the evidence for it.

## 3. Mitigate

Pick the smallest reversible action that stops the impact:

- Change shipped in the window → roll back the deploy or turn off the feature flag.
- Load spike → scale out or rate-limit.
- One bad instance or zone → drain it.
- Dependency down → fail over or degrade the feature.

Ask the user first before each action. Say the exact command, the expected effect, and how to undo it. After the
action, check the same metric that showed the symptom.

## 4. Communicate

1. P0/P1: post a status update every 30 minutes, even with no news: impact, current action, next update time.
2. State facts and the next step. Do not guess the root cause in public updates.

## 5. Resolve and hand off

1. Call the incident resolved when the symptom metric is back in its normal range for 15 minutes.
2. If you hand off to another person, pass the timeline, the current hypothesis, the actions taken, and open
   risks.
3. Write the incident page `docs/incidents/<YYYY-MM-DD>-<id>.md`: impact, root cause with evidence, fix with
   link and regression test, prevention actions with owners.

## 6. Find the root cause

1. Ask "why" from the symptom back to the defect until the answer is a change you can make in code, config,
   tests, alerts, or limits. "Human error" is not a root cause; ask why the system allowed it.
2. Add at least one prevention action: a test, an alert, a limit, or a rule.
3. Link the fix and its regression test in the incident page.
