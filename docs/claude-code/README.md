---
covers:
  - src/claude.rs
  - extensions/claude/**
---

# Claude Code integration

Agentic 1.4.0 installs native Claude Code assets. Claude Code now gets the same
features as OpenCode and Codex.

## What gets installed

```sh
agentic install --project-dir <dir> --agent-os claude --areas software \
  --specializations software.backend,software.general \
  [--claude-profile anthropic|none] [--enable-jev] [--enable-telegram]
```

| Path | Content | Notes |
| --- | --- | --- |
| `.claude/CLAUDE.md` | `@../AGENTS.md` and `@../MEMORY.md` imports, layout, SDLC order | Loaded automatically at session start. With `--agents-md keep` it imports `@../.agent/AGENTS.md` instead, because root `AGENTS.md` belongs to the project ([details](../agentic-reference.md#root-agentsmd-generate-or-keep)) |
| `.claude/agents/*.md` | 9 role subagents with `tools:` and, with a profile, `model:` | `instruction-reviewer` and `memory-curator` are read-only |
| `.claude/rules/*.md` | Specialization rules | Loaded automatically; every rule loads in every session |
| `.claude/skills/<name>/SKILL.md` | Specialization skills | Each `name` matches its directory; Claude loads a skill by its description |
| `.claude/commands/<id>.md` | Thin wrapper per workflow (`description`, `argument-hint`) | Runs `.agent/workflows/<id>.md`, which stays the single source. A company workflow gets the same wrapper and replaces the pack command with the same id. A role-neutral workflow (no `roles`, no `execution.initiator`) runs in the main session: `lean` does every step itself; `team` sends each step to the installed role agent that fits it (`developer` for code, `qa` for verification, `devops-engineer` for infrastructure), one subagent per step at most |
| `.claude/settings.json` | `agent: product-owner`, `enabledMcpjsonServers`, optional JEV and Telegram hooks | Each entry is ownership-tracked (see below) |
| `.mcp.json` | Selected MCP servers (Context7, MemPalace, Playwright, …) | Same registry as OpenCode and Codex |
| `.agent/{rules,skills,workflows}` | Shared copies for every host | Workflows are read from here |

## SDLC team

Claude subagents cannot start other subagents. `product-owner` therefore runs as
the main session: the `agent` setting is written only when it is absent, and you
can also start it with `claude --agent product-owner`. The main session delegates
through the Agent tool with `subagent_type` set to the role name:

`product-owner` → `team-lead` → `developer` → `qa` → optional `devops-engineer` →
acceptance → post-task review (`instruction-reviewer` + `memory-curator`).
`pm` and `analyst` (system analyst: requirements, scenarios, API/data contracts,
UX states) are optional.

## Model profiles

The `anthropic` profile (`extensions/claude/profiles/anthropic/profile.json`) is
the default. It pins model aliases per role:

| Alias | Roles |
| --- | --- |
| `opus` | product-owner, team-lead |
| `sonnet` | developer, qa, devops-engineer, analyst |
| `haiku` | pm, instruction-reviewer, memory-curator |

- `--claude-profile none` (or `AGENTIC_CLAUDE_PROFILE=none`) removes `model:`, so
  every role inherits the session model.
- The choice is saved in `.agentic.json` (`settings.claude_profile`), and
  `agentic upgrade` replays it.
- When JEV is enabled, `model:` is left out so the JEV hooks can choose an alias
  for each spawn (see [JEV](../jev-integration/README.md#claude-code-adapter)).

## Settings ownership

`.claude/settings.json` belongs to the user. Agentic only adds entries and records
each one:

- `.agentic/claude-settings-entries.json`: `agent` and the server names added to
  `enabledMcpjsonServers`.
- `.agentic/claude-jev-hook-entries.json` and `.agentic/claude-notify-hook-entries.json`:
  one hook group per event.

On disable or a later install, Agentic removes only its own entries that still
match the recorded value. It never changes a user-edited value, never writes
`settings.local.json`, and skips a `settings.json` that is not valid JSON, with a
warning.

## Role rename migration (1.4.0)

`designer` → `analyst`, `instruction_reviewer` → `instruction-reviewer`,
`memory_curator` → `memory-curator`, on every host.

- `agentic install` and `agentic upgrade` delete old role files whose content
  still matches the manifest hash.
- Edited old files are kept, and a warning asks you to merge them by hand.
- Old role keys are removed from the managed `opencode.json` agent and
  `permission.task` maps.
- The JEV runtime accepts both spellings.

## Acceptance criteria

- `/agents` lists the nine roles; `/develop-feature …` and the other installed
  workflows appear as slash commands; installed skills are available.
- `.claude/rules/*.md`, `AGENTS.md` (`.agent/AGENTS.md` with `--agents-md keep`) and `MEMORY.md` load at
  session start.
- Reviewers cannot write files (`tools: Read, Grep, Glob`).
- Re-running install is idempotent; disabling a feature removes only owned entries.
- `make blackbox-claude` verifies this with the real CLI (see the
  [JEV docs](../jev-integration/README.md#real-local-blackbox)).

## Operational notes

- Hooks run `python3 "$CLAUDE_PROJECT_DIR/…"`, so Python 3.10+ is required when JEV
  or Telegram is enabled.
- Every rule in `.claude/rules/` has no `paths:` filter, so all rules load in
  every session. Add `paths:` to a rule to load it only for matching files.
