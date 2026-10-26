---
description: Show or switch the Agentic role profile of this project (list | lean | team | <custom id>)
argument-hint: "[list | <profile-id>]"
---

Agentic profile request: $ARGUMENTS

1. If the request is empty or `list`, run `agentic profile list --host claude` in the project root and show
   the output. Stop.
2. Otherwise run `agentic profile use <id>` in the project root, where `<id>` is the requested profile. Add
   `--host claude` only when the user asks to change Claude Code alone.
3. Report the files that the command added, removed, or preserved.
4. Tell the user to restart the Claude Code session. The new role agents load only in a new session.

Do not edit agent files by hand. If the command fails, show its error and stop.
