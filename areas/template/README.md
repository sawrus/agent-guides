# Template — authoring guide

Use these templates when adding a new specialization area, spec, skill, workflow, rule, or prompt to agent-guides.

## Templates

| File | Use for |
|:---|:---|
| `AGENTS-area.tmpl.md` | Root `AGENTS.md` for a new domain area (e.g., `areas/design/`) |
| `AGENTS.tmpl.md` | Spec-level `AGENTS.md` (e.g., `areas/design/copywriting/AGENTS.md`) |
| `skill.tmpl.md` | A new `skills/{{name}}/SKILL.md` |
| `workflow.tmpl.md` | A new `workflows/{{name}}.md` |
| `rule.tmpl.md` | A new `rules/{{name}}.md` |
| `prompt.tmpl.md` | A new `prompts/{{name}}.md` |
| `PROMPTS.tmpl.md` | The `PROMPTS.md` index for a spec |

## Authoring checklist

Every rule, skill, and workflow must meet [docs/artifact-standard.md](../../docs/artifact-standard.md). Before
opening a PR with new content:

- [ ] All `{{PLACEHOLDER}}` values replaced and all `AGENT INSTRUCTIONS` comment blocks deleted.
- [ ] `make check-artifacts` reports no new findings for the files you changed.
- [ ] Rules are scoped by `paths:` (or `trigger: manual`) and list checkable imperatives.
- [ ] Skills state their trigger in `description` ("Use when ...") and are procedures, not overviews.
- [ ] Workflow steps each have **Do** and a checkable **Done when**; no roles and no report files.
- [ ] Prompt examples contain no placeholders; both EN and RU blocks present.
- [ ] Spec map in `AGENTS.md` matches the actual files on disk.

## File naming conventions

- Skill directories: `kebab-case/` (e.g., `api-design/`)
- Workflow files: `kebab-case.md` (e.g., `create-endpoint.md`)
- Rule files: `kebab-case.md` (e.g., `migration-safety.md`)
- Prompt files: match workflow name (e.g., `create-endpoint.md`)

## Size limits

| File type | Limit |
|:---|:---|
| Area `AGENTS.md` | ≤ 100 lines |
| Spec `AGENTS.md` | ≤ 80 lines |
| Rule | ≤ 80 lines and ≤ 1,200 tokens (ART-R3) |
| `SKILL.md` | ≤ 250 lines; references and assets ≤ 400 lines (ART-S3) |
| Workflow | ≤ 120 lines and ≤ 1,800 tokens, 3–6 steps (ART-W2, ART-W4) |
| Prompt | no hard limit, but examples must be self-contained |

## Checks in workflows

The `checks` field lists commands that must pass, for example `make test`. A check is a command with an exit code,
not a judgement such as "output looks professional".
