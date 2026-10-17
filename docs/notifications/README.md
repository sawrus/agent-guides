# Telegram notifications

Agentic sends a Telegram message when an agent finishes its turn and when it
waits for input. All hosts use one script (`.agent/notify/telegram.py`), one
switch, one credential store and one message format.

| Host | Mechanism | Finished | Waiting for input |
| --- | --- | --- | --- |
| OpenCode V2 (2.0.28+) | Plugin `.opencode/plugins/telegram-notification.ts` → script | `session.execution.succeeded` (root sessions only) | `permission.asked`, `question.asked` |
| Claude Code | Hooks in `.claude/settings.json` → script | `Stop` | `Notification` (`permission_prompt`, `idle_prompt`) |
| Codex | Hooks in `.codex/hooks.json` → script | `Stop` | `PermissionRequest` |

## Enable

```sh
agentic install --project-dir <dir> --agent-os opencode,claude,codex ... --enable-telegram
```

- Interactive installs ask for the bot token and chat id. They are stored in
  `~/.config/agentic/config.json`, never in the project.
- `--disable-telegram` removes only the hook groups that Agentic owns
  (`.agentic/claude-notify-hook-entries.json`, `.agentic/codex-notify-hook-entries.json`).
- The project switch is `settings.notifications.telegram.enabled` in `.agentic.json`.
  The script also accepts the older `settings.opencode_plugins.telegram.enabled`.
- Codex requires a trust review of the new hooks in `/hooks`.
- OpenCode loads the plugin from `.opencode/plugins/` automatically. Releases before
  1.4.0 also listed `telegram-notification` in the `opencode.json` `plugin` array, which
  OpenCode V2 treats as an npm package (install fails with 404). `agentic install` and
  `agentic upgrade` remove that entry.

## Message format

```
✅ Задача завершена — <project> · <host>
<session title, OpenCode only>

<final answer>
```

```
⏳ Ожидает ввода — <project> · <host>

<reason: permission, question with options, or idle prompt>
<command or resources as a code block>
```

- The agent's Markdown is rendered with Telegram HTML: bold, italic, strikethrough,
  inline code, fenced code blocks, headings (bold), bullet lists, quotes and
  `https://` links. Tables become aligned monospace blocks. Project-relative links
  show the path instead of a dead link.
- When Telegram rejects the markup (HTTP 400) or the rendered text exceeds 4096
  characters, the same message is resent as plain text, and the reason goes to the
  debug log.
- An answer of 4096 characters or more is sent as `response-<session>.md` with
  `sendDocument`, followed by a message with a preview of about 3000 characters,
  cut at a line boundary.
- Link previews are disabled.

The final answer comes from `last_assistant_message` when the host supplies it,
otherwise from the Claude transcript (`transcript_path`), or, for OpenCode, from the
last `session.text.ended` event of the turn. A Claude `Stop` event with
`stop_hook_active` is skipped. OpenCode subagent sessions are not reported.

## Runtime behavior

- The script prints `{}` and exits 0 at once. A detached child process sends the
  message, so Telegram latency never blocks the agent.
- The OpenCode plugin collects the title and answer from the event stream and
  starts the script detached, so delivery also completes when `opencode run` stops
  its server right after the turn.
- Errors go to `.agentic/telegram-debug.log`, with the token and chat id redacted.
- Missing credentials or a disabled switch mean nothing is sent.
- Python 3 must be on `PATH` (`python3`; `python` on Windows).

| Variable | Purpose |
| --- | --- |
| `AGENTIC_TELEGRAM=0` | Turns notifications off for one process |
| `AGENTIC_TELEGRAM_API_BASE_URL` | Bot API base URL; `OPENCODE_TELEGRAM_API_BASE_URL` is also accepted |
| `AGENTIC_CONFIG_DIR` | Credential directory (tests and blackbox runs) |

## Verification

- `make test-notify` runs the offline tests against a fake Bot API (formatting,
  plain-text fallback, attachments, waiting events for all hosts).
- `make blackbox` / `make blackbox-<host>` check that the real CLI delivers the
  final answer to a local fake API (`telegram_fired`).
- 2026-10-16: OpenCode 2.0.29 delivered both events through the plugin to a real
  bot and to the fake API; Claude Code and Codex `Stop` hooks fired in real blackbox
  runs.
