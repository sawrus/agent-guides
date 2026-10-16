# Telegram notifications

Agentic sends a Telegram message when an agent finishes a reply. Claude Code also
sends one when it waits for input. All hosts share one switch and one credential
store.

| Host | Mechanism | Events |
| --- | --- | --- |
| OpenCode | Plugin `.opencode/plugins/telegram-notification.ts` | `session.idle` |
| Claude Code | Hooks in `.claude/settings.json` → `.agent/notify/telegram.py` | `Stop`; `Notification` (`permission_prompt`, `idle_prompt`) |
| Codex | Hooks in `.codex/hooks.json` → `.agent/notify/telegram.py` | `Stop`; `PermissionRequest` |

## Enable

```sh
agentic install --project-dir <dir> --agent-os claude,codex ... --enable-telegram
```

- Interactive installs ask for the bot token and chat id. They are stored in
  `~/.config/agentic/config.json`, never in the project.
- `--disable-telegram` removes only the hook groups that Agentic owns
  (`.agentic/claude-notify-hook-entries.json`, `.agentic/codex-notify-hook-entries.json`).
- The project switch is `settings.notifications.telegram.enabled` in `.agentic.json`.
  The script also accepts the older `settings.opencode_plugins.telegram.enabled`.
- Codex requires a trust review of the new hooks in `/hooks`.

## Message format

The format is the same as the OpenCode plugin:

- Finished: `✅ Задача завершена — <project>`, a blank line, then the final assistant text.
- Waiting: `⏳ Ожидает ввода — <project>`, then the prompt or the tool and command.
- A text of 4096 characters or more is sent as `response-<session>.md` with
  `sendDocument`, followed by a message with the first 3000 characters.

The final text comes from `last_assistant_message` when the host supplies it.
Otherwise the script reads the Claude transcript (`transcript_path`). A `Stop`
event with `stop_hook_active` is skipped.

## Runtime behavior

- The hook prints `{}` and exits 0 at once. A detached child process sends the
  message, so Telegram latency never blocks the agent.
- Errors go to `.agentic/telegram-debug.log`, with the token and chat id redacted.
- Missing credentials or a disabled switch mean nothing is sent.

| Variable | Purpose |
| --- | --- |
| `AGENTIC_TELEGRAM=0` | Turns notifications off for one process |
| `AGENTIC_TELEGRAM_API_BASE_URL` | Bot API base URL; `OPENCODE_TELEGRAM_API_BASE_URL` is also accepted |
| `AGENTIC_CONFIG_DIR` | Credential directory (tests and blackbox runs) |

## Verification

- `make test-notify` runs the offline tests against a fake Bot API.
- `make blackbox-claude` checks that a real Claude `Stop` hook delivers the final
  answer to the local fake API.
