# AI Instructions

Before doing any work in this repository, read the file **AGENTS.md**.

AGENTS.md defines:
- agent roles
- development workflow
- rules for modifying the repository

Always follow the instructions from AGENTS.md.

## Gemini Subagents

- Shared project subagents for Gemini CLI live in `.gemini/agents/*.md`.
- This extension ships SDLC role subagents in `agents/` so they install into that path automatically.
- Gemini CLI subagents are currently a preview feature, so behavior and settings may evolve.
- If subagents are disabled in your Gemini settings, re-enable them before relying on these files.
- Invoke a specific role directly with `@agent-name`, for example `@team-lead` or `@qa`.
