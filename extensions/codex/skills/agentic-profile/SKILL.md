---
name: agentic-profile
description: "Shows or switches the Agentic role profile (lean, team, or a custom id) of this project; use when the user asks which roles are installed or asks to switch to lean, team, or another profile."
---

# Skill: Agentic role profile

## When to load

- The user asks which Agentic profile or role agents the project uses.
- The user asks to switch the project to `lean`, `team`, or a custom profile.

## Steps

1. To list profiles, run `agentic profile list --host codex` in the project root and show the output.
2. To switch, run `agentic profile use <id>` in the project root. Add `--host codex` only when the user asks
   to change Codex alone.
3. Report the files that the command added, removed, or preserved.
4. Tell the user to restart the Codex session. The new role agents load only in a new session.

The user can also run the command directly from the Codex prompt: `! agentic profile use team`.
Do not edit agent files by hand. If the command fails, show its error and stop.
