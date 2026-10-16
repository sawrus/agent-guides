# AI Instructions

@../AGENTS.md
@../MEMORY.md

Always follow the imported AGENTS.md: it defines agent roles, the development workflow, and the rules for changing this repository.

## Claude Code layout

- **Rules** load automatically from `.claude/rules/`. Do not read the duplicate copies in `.agent/rules/` again.
- **Skills** live in `.claude/skills/<name>/SKILL.md`. Claude loads a skill when its description matches the task.
- **Workflows** live in `.agent/workflows/` and run as slash commands from `.claude/commands/`, for example `/develop-feature <request>`.
- **Prompts** stay in `.agent/prompts/`. Load one only when the task or loaded guidance references it.
- **Role subagents** live in `.claude/agents/`. Delegate with the Agent tool and set `subagent_type` to the role name.

## SDLC team

The main session runs as `product-owner` (the `agent` setting in `.claude/settings.json`, or `claude --agent product-owner`). Subagents cannot start other subagents, so the main session coordinates every handoff:

1. `product-owner`: scope and acceptance criteria. Optional: `pm` for delivery planning, `analyst` for requirements and contracts.
2. `team-lead`: implementation plan and quality gates.
3. `developer`: implementation and tests.
4. `qa` with `team-lead` sign-off: verification and go / no-go.
5. Optional `devops-engineer`: CI/CD, infrastructure, and deployment changes.
6. `product-owner`: acceptance and delivery report.
7. Post-task review with `instruction-reviewer` and `memory-curator` (read-only). Run it only after successful delivery of a workflow that has a review hook, and follow `REVIEW_PIPELINE.md`.
