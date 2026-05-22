# Observability — guidance index

## What this area covers

Platform observability: Prometheus metrics and Alertmanager rules, Loki log aggregation, Tempo distributed tracing, Grafana dashboards, SLO implementation, and service monitoring onboarding.

## Guidance chain

1. Project `.agent/` baseline
2. `.agent/rules/*` — load all
3. `.agent/skills/*/SKILL.md` — load only the skill matching the current task
4. `.agent/workflows/*` — load the workflow matching the triggered command

## Cross-cutting constraints

- **Golden signals first** — every new service exposes latency, traffic, errors, and saturation before any custom metrics.
- **Alert on symptoms, not causes** — page on user-facing impact; use dashboards for internal diagnosis.
- **Data retention is policy, not default** — all retention periods must be explicitly configured and justified.
- **No alert without runbook** — every firing alert must link to a documented investigation path.

## Spec map

```text
.agent/
├── rules/
│   ├── golden-signals.md        ← required metrics per service, naming conventions
│   ├── alerting-standards.md    ← severity levels, routing, inhibition, runbook requirement
│   └── data-retention.md        ← retention tiers, cost caps, compliance minimums
├── skills/
│   ├── prometheus-alertmanager/SKILL.md  ← PromQL, recording rules, alert routing
│   ├── grafana-dashboards/SKILL.md       ← dashboard-as-code, variable design, panels
│   ├── log-aggregation/SKILL.md          ← LogQL, structured logging, label design
│   ├── distributed-tracing/SKILL.md      ← trace propagation, sampling, span attributes
│   └── slo-implementation/SKILL.md       ← burn-rate alerts, error budget dashboards
├── workflows/
│   ├── observability-stack-setup.md       ← /observability-stack-setup
│   ├── onboard-service-monitoring.md      ← /onboard-service-monitoring
│   └── alert-investigation.md             ← /alert-investigation
└── prompts/
    └── *.md
```

## Discovery patterns

- `.agent/rules/*.md`
- `.agent/skills/*/SKILL.md`
- `.agent/workflows/*.md`
- `.agent/prompts/*.md`
