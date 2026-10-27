# Template — authoring guide

Use these templates when adding a new specialization area, spec, skill, workflow, or rule to agent-guides.

## Templates

| File | Use for |
|:---|:---|
| `AGENTS-area.tmpl.md` | Root `AGENTS.md` for a new domain area (e.g., `areas/design/`) |
| `AGENTS.tmpl.md` | Spec-level `AGENTS.md` (e.g., `areas/design/copywriting/AGENTS.md`) |
| `skill.tmpl.md` | A new `skills/{{name}}/SKILL.md` |
| `workflow.tmpl.md` | A new `workflows/{{name}}.md` |
| `rule.tmpl.md` | A new `rules/{{name}}.md` |

## Authoring checklist

Every rule, skill, and workflow must meet [docs/artifact-standard.md](../../docs/artifact-standard.md). Before
opening a PR with new content:

- [ ] All `{{PLACEHOLDER}}` values replaced and all `AGENT INSTRUCTIONS` comment blocks deleted.
- [ ] `make check-artifacts` reports no new findings for the files you changed.
- [ ] Rules are scoped by `paths:` (or `trigger: manual`) and list checkable imperatives.
- [ ] Skills state their trigger in `description` ("Use when ...") and are procedures, not overviews.
- [ ] Workflow steps each have **Do** and a checkable **Done when**; no roles and no report files.
- [ ] Each workflow has one `Example request:` line without placeholders.
- [ ] The spec `AGENTS.md` lists exactly the files on disk.

## File naming conventions

- Skill directories: `kebab-case/` (e.g., `api-design/`)
- Workflow files: `kebab-case.md` (e.g., `add-migration.md`)
- Rule files: `kebab-case.md` (e.g., `migration-safety.md`)

## Size limits

| File type | Limit |
|:---|:---|
| Area `AGENTS.md` | ≤ 60 lines |
| Spec `AGENTS.md` | ≤ 8 lines (installed always-on) |
| Rule | ≤ 80 lines and ≤ 1,200 tokens (ART-R3) |
| `SKILL.md` | ≤ 250 lines; references and assets ≤ 400 lines (ART-S3) |
| Workflow | ≤ 120 lines and ≤ 1,800 tokens, 3–6 steps (ART-W2, ART-W4) |

## Checks in workflows

The `checks` field lists commands that must pass, for example `make test`. A check is a command with an exit code,
not a judgement such as "output looks professional".
