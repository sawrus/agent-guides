# Frontend — guidance index

## What this area covers

UI and component development: component architecture, accessibility (WCAG AA), performance budgets, state management, API integration, CSS architecture, visual regression, and bundle analysis.

## Guidance chain

1. Project `.agent/` baseline (`AGENTS.md` + `.agent/*`)
2. `software/general/rules/*` — always active
3. `frontend/rules/*` — load all for this spec
4. `frontend/skills/*/SKILL.md` — load only the skill matching the current task
5. `frontend/workflows/*` — load the workflow matching the triggered command

## Inherited from general

- SDLC roles and quality gates
- Git workflow, CI, linting / formatting, code style
- Shared delivery and code review workflows

## Frontend-specific constraints

- WCAG AA compliance is a baseline requirement, not an enhancement — accessibility defects are P0.
- Performance budgets must be defined before implementing new features with significant asset load.
- No component ships without documented states: loading, empty, error, success, permission-denied.

## Spec map

```text
frontend/
├── rules/
│   ├── accessibility.md    ← WCAG AA requirements, ARIA patterns, keyboard navigation
│   ├── architecture.md     ← component hierarchy, coupling, folder structure
│   ├── performance.md      ← Core Web Vitals budgets, lazy loading, asset optimization
│   └── quality.md          ← snapshot stability, coverage thresholds, PR review criteria
├── skills/
│   ├── a11y-audit/SKILL.md           ← axe, Lighthouse, screen reader testing patterns
│   ├── api-integration/SKILL.md      ← data fetching, error boundaries, loading states
│   ├── component-design/SKILL.md     ← composition, props contracts, Storybook patterns
│   ├── css-architecture/SKILL.md     ← utility-first, design tokens, style isolation
│   ├── error-handling/SKILL.md       ← error boundaries, fallback UI, user messaging
│   ├── performance-tuning/SKILL.md   ← bundle splitting, image optimization, CWV analysis
│   ├── state-management/SKILL.md     ← local vs server state, caching, optimistic UI
│   └── testing-patterns/SKILL.md     ← component tests, mocking, visual regression
├── workflows/
│   ├── a11y-fix.md              ← /a11y-fix
│   ├── bundle-analyze.md        ← /bundle-analyze
│   ├── release-prep.md          ← /release-prep
│   ├── scaffold-component.md    ← /scaffold-component
│   └── visual-regression.md     ← /visual-regression
└── prompts/
    └── *.md
```

## Discovery patterns

- `rules/*.md`
- `skills/*/SKILL.md`
- `workflows/*.md`
- `prompts/*.md`
