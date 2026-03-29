# Infrastructure — guidance index

## What this area covers

Infrastructure-as-Code lifecycle: Terraform module authoring, environment provisioning and destruction, drift detection and remediation, state management, Ansible playbooks, cost optimization, and secret hygiene.

## Guidance chain

1. Project `.agent/` baseline
2. `infrastructure/rules/*` — load all
3. `infrastructure/skills/*/SKILL.md` — load only the skill matching the current task
4. `infrastructure/workflows/*` — load the workflow matching the triggered command

## Cross-cutting constraints

- **IaC-only changes** — zero manual console or CLI changes in non-development environments; document exceptions.
- **State is sacred** — never manually edit Terraform state; always use `terraform state` commands with documented justification.
- **Immutability over mutation** — replace resources rather than patching them in place where possible.
- **Secret hygiene** — no credentials, tokens, or keys in IaC code, state, or commit history.

## Spec map

```text
infrastructure/
├── rules/
│   ├── iac-standards.md       ← module structure, naming, provider pinning
│   ├── immutability.md        ← replace-before-destroy, no in-place secret mutations
│   ├── secret-hygiene.md      ← vault integration, forbidden patterns, rotation policy
│   └── state-management.md   ← backend config, state locking, import procedures
├── skills/
│   ├── terraform-modules/SKILL.md    ← module authoring, variable design, output contracts
│   ├── ansible-playbooks/SKILL.md    ← idempotency, role structure, vault integration
│   ├── drift-detection/SKILL.md      ← plan-diff analysis, scheduled drift checks
│   ├── state-management/SKILL.md     ← import, mv, rm, split-state patterns
│   └── cost-optimization/SKILL.md   ← right-sizing, reserved capacity, unused resource cleanup
├── workflows/
│   ├── provision-environment.md   ← /provision-environment
│   ├── destroy-environment.md     ← /destroy-environment
│   ├── drift-remediation.md       ← /drift-remediation
│   └── module-development.md      ← /module-development
└── prompts/
    └── *.md
```

## Discovery patterns

- `rules/*.md`
- `skills/*/SKILL.md`
- `workflows/*.md`
- `prompts/*.md`
