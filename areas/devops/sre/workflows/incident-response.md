---
name: incident-response
type: workflow
trigger: /incident-response
description: Investigate an alert or production incident, mitigate it, fix the cause, and write the incident page.
inputs:
  - alert_or_symptom
  - affected_service
outputs:
  - mitigation
  - fix
  - incident_page
selection:
  general: false
  use-when: "The request reports a firing alert, an outage, elevated errors or latency, a database incident, or asks for a postmortem of a production event."
  avoid-when: "A bug found in development or tests with no production impact; use the debug workflow."
uses-skills:
  - incident-command
related-rules:
  - on-call-standards.md
  - slo-policy.md
artifacts:
  - docs/incidents/<YYYY-MM-DD>-<id>.md
---

# Respond to an incident

Example request: `/incident-response "order-service returns 100% 5xx since 15:42 UTC, checkout is down"`

## Steps

### 1. Assess impact

- **Do:** read the alert, the dashboard, and the SLO burn rate. Record what fails, for whom, and since when.
  Set the severity from `on-call-standards.md`. Read-only queries (logs, metrics, `kubectl get`, `describe`)
  are allowed; ask the user first before any command that changes production.
- **Done when:** the incident has a severity, a start time, and one sentence of user impact.

### 2. Mitigate

- **Do:** pick the fastest safe action from the evidence: roll back the last deploy, turn off a feature flag,
  scale out, fail over, or block bad traffic. Ask the user first and state the exact command before you run it.
- **Done when:** the error rate or latency is back under the SLO threshold for 15 minutes, or the user decides
  to stop mitigation.

### 3. Find the root cause

- **Do:** build a timeline from deploys, config changes, alerts, and logs. Test each hypothesis against data
  (queries, commits, traces) until one cause explains all symptoms. For a database incident, include slow
  queries, locks, replication lag, and connection counts. Use read-only access; ask the user first before
  a query that could load the production database.
- **Done when:** the cause is backed by evidence and is not "human error".

### 4. Fix and prevent

- **Do:** change the code, config, or alert that allowed the failure, with a regression test or a check. Add at
  least one prevention item (test, alert, limit, rule) with an owner. Ask the user first before you deploy it.
- **Done when:** the fix is in a change with green checks and each prevention item has an owner.

### 5. Write the incident page

- **Do:** write `docs/incidents/<YYYY-MM-DD>-<id>.md` with `covers:` for the changed code and the sections
  impact, root cause with evidence, fix with link and test, and prevention with owners.
- **Done when:** the page has all four sections and links the fix change.
