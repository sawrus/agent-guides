# QA — guidance index

## What this area covers

Test strategy, risk-based verification, and release confidence: test pyramid design, flakiness management, performance auditing, regression suite maintenance, test data management, and accessibility testing.

## Guidance chain

1. Project `.agent/` baseline (`AGENTS.md` + `.agent/*`)
2. `.agent/rules/*` — always active
3. `.agent/rules/*` — load all for this spec
4. `.agent/skills/*/SKILL.md` — load only the skill matching the current task
5. `.agent/workflows/*` — load the workflow matching the triggered command

## Inherited from general

- SDLC role responsibilities and handoffs
- Git / CI / lint / format quality baseline
- Shared development and review workflows

## QA-specific constraints

- Flaky tests must be quarantined within one business day; they are never silently skipped.
- Go / no-go recommendation must be written with evidence — "looks good" is not a QA output.
- Every test data set must be deterministic and resettable; no dependency on production data.

## Spec map

```text
.agent/
├── rules/
│   ├── test-strategy.md       ← pyramid ratios, coverage targets, risk classification
│   ├── quality-gates.md       ← blocking vs advisory criteria, merge conditions
│   ├── flakiness-policy.md    ← quarantine SLA, fix-or-delete policy, flakiness budget
│   └── test-data.md           ← data isolation, factory patterns, PII handling in tests
├── skills/
│   ├── test-pyramid/SKILL.md             ← unit/integration/e2e ratios, boundary decisions
│   ├── e2e-patterns/SKILL.md             ← Playwright/Cypress patterns, page objects
│   ├── api-testing/SKILL.md              ← contract tests, mutation testing, schema validation
│   ├── performance-testing/SKILL.md      ← k6, Lighthouse, load profiles, threshold design
│   ├── accessibility-testing/SKILL.md    ← axe-core, manual checks, WCAG AA criteria
│   └── test-data-management/SKILL.md     ← factories, seeds, snapshot isolation
├── workflows/
│   ├── smoke-test.md                  ← /smoke-test
│   ├── regression-suite.md            ← /regression-suite
│   ├── flakiness-investigation.md     ← /flakiness-investigation
│   ├── performance-audit.md           ← /performance-audit
│   └── test-coverage-report.md        ← /test-coverage-report
└── prompts/
    └── *.md
```

## Discovery patterns

- `.agent/rules/*.md`
- `.agent/skills/*/SKILL.md`
- `.agent/workflows/*.md`
- `.agent/prompts/*.md`
