---
description: Required labels, severities, burn-rate alerts, and routing for Prometheus alert rules and Alertmanager config.
paths:
  - "**/alerts/**"
  - "**/*rules*.yml"
  - "**/*rules*.yaml"
  - "**/prometheus/**"
  - "**/alertmanager*.yml"
  - "**/alertmanager*.yaml"
  - "**/*prometheusrule*.yaml"
---

# Alerting standards

- Add `severity`, `service`, and `team` labels and a `runbook_url` annotation to every alert rule.
- Use only the severities `critical` (pages on-call), `warning` (team channel), and `info` (no notification).
- Page only on symptoms that users see (error rate, latency, availability); route cause alerts such as CPU or disk to `warning` or `info`.
- Define a fast-burn alert (1 h and 5 min windows, burn rate 14.4) and a slow-burn alert (6 h and 30 min windows, burn rate 6) for every SLO.
- Route fast-burn alerts as `critical` and slow-burn alerts as `warning`.
- Set a `for:` duration of at least `2m` on every alert that is not a burn-rate alert.
- Delete or rewrite an alert that fired 5 times in 30 days without a human action.
- Route alerts in Alertmanager by the `team` and `environment` labels; never page on-call for non-production alerts.
- Set `repeat_interval` and an escalation receiver for unacknowledged `critical` alerts.
- Add `inhibit_rules` so a cluster-wide or upstream alert suppresses the dependent service alerts.
- Create silences with an author, a comment, and an end time; never create a silence without an end time.
- Test every alert rule file with `promtool check rules` and `promtool test rules` in CI.
- Limit auto-remediation to reversible actions (restart a stateless pod) and emit an event for every automatic action.
