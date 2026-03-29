# SRE — guidance index

## What this area covers

Site reliability engineering: SLO/SLI design, error budget policy, chaos engineering, capacity planning, incident command, and post-mortem facilitation. The SRE area treats reliability as a measurable feature with a finite budget — not a vague aspiration.

## Guidance chain

1. Project `.agent/` baseline
2. `sre/rules/*` — load all
3. `sre/skills/*/SKILL.md` — load matching skill only
4. `sre/workflows/*` — load matching workflow

## Cross-cutting constraints

- **SLOs drive decisions** — if error budget remains, ship features; if exhausted, halt features and fix reliability.
- **No heroics** — every repeated manual action is a toil item to automate.
- **Blameless culture** — incidents indict systems, not people. Post-mortems focus on what the system lacked.
- **Data before action** — no reliability work starts without a metric showing the problem.

## Spec map

```text
sre/
├── rules/
│   ├── slo-policy.md             ← SLO definition standards, window sizes, target tiers
│   ├── error-budget-policy.md    ← budget consumption thresholds, freeze triggers
│   └── on-call-standards.md      ← rotation design, escalation, response SLAs
├── skills/
│   ├── slo-sli-design/SKILL.md       ← SLI selection, SLO target setting, burn-rate alerts
│   ├── chaos-engineering/SKILL.md    ← experiment design, blast radius, rollback gates
│   ├── capacity-planning/SKILL.md    ← demand forecasting, right-sizing, headroom models
│   ├── incident-command/SKILL.md     ← severity classification, role assignment, comms cadence
│   └── postmortem-analysis/SKILL.md  ← 5 Whys, fault trees, systemic action items
├── workflows/
│   ├── incident-response.md   ← /incident-response
│   ├── postmortem.md          ← /postmortem
│   └── slo-review.md          ← /slo-review
└── prompts/
    └── *.md
```

## Discovery patterns

- `rules/*.md`
- `skills/*/SKILL.md`
- `workflows/*.md`
- `prompts/*.md`
