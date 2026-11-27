---
covers:
  - src/update_check.rs
  - extensions/codex/hooks/gate/gate.py
---

# Upgrade reminder

agentic tells you once per interval (default 7 days, per machine) that a newer release exists. It only offers the
upgrade. It never upgrades by itself.

## What you see

The reminder runs at session start in Claude Code, Codex, and OpenCode. It rides on the quality gate session-start
runtime (`gate.py --event start`), so it works where the gate is installed (the default; `--disable-gate` removes
it). The gate calls the hidden command `agentic __update-check --format claude|codex|opencode`. The logic lives
in `src/update_check.rs`.

| Host | User sees it | Agent gets |
|---|---|---|
| Claude Code | `systemMessage` of the `SessionStart` hook (shown to the user) | one `additionalContext` line: mention it in the first reply if the user did not see it; run the upgrade only after the user agrees |
| Codex | `systemMessage` of the `SessionStart` hook (shown as a UI warning) | the same line |
| OpenCode | no user channel: the server plugin API has no toast (the toast API `context.ui.toast` exists only in a TUI plugin) | one system line: say this in the first reply, offer the upgrade, run it only after the user agrees |

Example text:

```text
agentic v15.0.0 is available (installed v14.0.1). Run `agentic upgrade` to update the binary and this
project's agentic files. The next reminder comes in 7 days.
```

## The command to run

`agentic upgrade` downloads the newest release from GitHub Releases, replaces the installed binary, and then
synchronizes the agentic files of the current project with the new binary. Run it in the project directory. The
agent runs it only after you answer yes. To refresh files without a binary update, see
[`AGENTIC_SKIP_BINARY_UPGRADE`](agentic-reference.md#upgrade-behavior).

## Interval and switches

- `~/.config/agentic/config.json`: `{"update_check": {"interval_days": 7}}`. `0` turns the reminder off. Other
  keys in the file stay as they are. There is no `agentic config` command; edit the file.
- `AGENTIC_UPDATE_CHECK=0` (also `off`, `false`, `no`) turns it off for one shell or CI, whatever the file says.
- `GITHUB_TOKEN` or `GH_TOKEN` is optional authentication for the GitHub API rate limit. agentic sends it only
  to github.com (not when `GH_HOST` names another host), retries once without it on 401 or 403, and never prints
  or stores it.

## State and snooze

The state lives in `~/.cache/agentic/update-check.json` (`$XDG_CACHE_HOME/agentic/`), once per machine, not per
project: `last_check_at`, `last_notified_at`, `latest_seen`. The check runs only when the interval since
`last_check_at` has passed. A shown reminder counts as the check, so the next reminder comes after the next
interval, also when you ignore or decline it. A newer release that appears earlier waits for the interval.

## Sessions without a human

The snooze is machine-wide, so a session with no human must not use it up. The hook skips the reminder and leaves
the state untouched for OpenCode child sessions, for Claude Code and Codex subagents (`agent_id` in the hook
input), and when `CI` is set. The Claude Code and Codex docs name no field or variable for `claude -p` or
`codex exec`, so agentic cannot detect them. Scripts and benchmark harnesses that launch agents set
`AGENTIC_UPDATE_CHECK=0` (`scripts/pilot_jev.py` does).

## Safety

- If the state file cannot be saved, the hook skips the lookup (no network at every session). Writes are atomic
  (temp file and rename), so concurrent sessions never read half a file.
- Known limitation: on Windows, a hook that starts `agentic` through the npm shim may exceed the 4 s limit. The
  reminder then stays silent.

- The lookup has a 2 s limit, and the hook gives the binary 4 s. A missing binary, a network error, bad JSON, or
  an old binary without the command ends in silence.
- The attempt is recorded before the lookup, so a failing network is not retried at every session.
- Versions compare as numbers (`14.10.0` is newer than `14.9.0`). Pre-releases and drafts are ignored.
- Tests use `AGENTIC_UPDATE_CHECK_LATEST=<tag>` instead of the network. It is a test hook, not a setting.
