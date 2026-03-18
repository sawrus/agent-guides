# General Software Development guidance index

This area contains shared SDLC baseline guidance inherited by specialization areas.

## Inheritance contract

All specialization areas should follow this chain:

`AGENTS.md (scope) -> rules (constraints) -> skills (execution patterns) -> workflows (orchestration)`

Specializations must reference general guidance and only keep domain-specific overrides.

## Guidance tree

```text
general/
├── rules/
│   ├── git-workflow-guide.md
│   ├── github-workflow-guide.md
│   ├── gitlab-ci-guide.md
│   ├── makefile-guide.md
│   ├── docker-compose-guide.md
│   ├── lint-format-guide.md
│   ├── sdlc-methodology-guide.md
│   ├── sdlc-role-responsibilities.md
│   ├── readme-sync-guide.md
│   └── code-style-guide.md
├── skills/
│   └── general-dev-tools/SKILL.md
└── workflows/
    ├── project-setup-workflow.md
    ├── code-review-workflow.md
    └── development-cycle-workflow.md
```

## Discovery patterns

- `rules/*.md`
- `skills/*/SKILL.md`
- `workflows/*.md`
