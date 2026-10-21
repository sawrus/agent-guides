# AI Instructions

@../AGENTS.md

## Claude Code layout

- `.claude/rules/` holds only always-on and path-scoped rules; Claude loads them itself. On-demand rules stay in
  `.agent/rules/`; read one only when `AGENTS.md` or a loaded skill or workflow points to it.
- Skills live in `.claude/skills/<name>/SKILL.md`. Do not read the copies in `.agent/skills/`.
- Workflows live in `.agent/workflows/` and run as slash commands from `.claude/commands/`.
- Use native plan mode and todos for planning. Use subagents only as `AGENTS.md` "Scale the process to the
  task" allows.
