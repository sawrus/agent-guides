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

Before opening a PR with new content:

- [ ] All `{{PLACEHOLDER}}` values replaced with real content.
- [ ] All `AGENT INSTRUCTIONS` comment blocks deleted.
- [ ] Frontmatter fields fully populated (no empty values).
- [ ] Skill "When to load" section is specific and actionable.
- [ ] Rule constraints use imperative language: "must", "never", "required", "forbidden".
- [ ] Workflow steps each have: `@role`, Input, Actions, and a checkable "Done when" criterion.
- [ ] Prompt examples contain no placeholders; both EN and RU blocks present.
- [ ] File stays within line-count targets (skill: 150–350; workflow: 60–200; rule: < 150).
- [ ] Spec map in `AGENTS.md` matches the actual files on disk.

## File naming conventions

- Skill directories: `kebab-case/` (e.g., `api-design/`)
- Workflow files: `kebab-case.md` (e.g., `create-endpoint.md`)
- Rule files: `kebab-case.md` (e.g., `migration-safety.md`)
- Prompt files: match workflow name (e.g., `create-endpoint.md`)

## Line count targets

| File type | Target |
|:---|:---|
| Area `AGENTS.md` | ≤ 100 lines |
| Spec `AGENTS.md` | ≤ 80 lines |
| `SKILL.md` | 150–350 lines |
| Workflow | 60–200 lines |
| Rule | ≤ 150 lines |
| Prompt | no hard limit, but examples must be self-contained |

## Guidance on quality gates

Quality gates in workflows must be **objectively checkable** without human judgment:

❌ Bad: "Output looks professional."
✅ Good: "All required frontmatter fields are populated; file is under 350 lines; no `{{PLACEHOLDER}}` strings remain."

❌ Bad: "Tests pass."
✅ Good: "All unit tests in `src/__tests__/` pass with exit code 0 when run with `npm test`."
