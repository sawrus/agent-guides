---
covers:
  - extensions/codex/hooks/notify/**
  - extensions/opencode/plugins/telegram-notification.ts
  - src/notify.rs
---

# Telegram notifications

Agentic sends a Telegram message when an agent finishes its turn and when it
waits for input. All hosts use one script (`.agent/notify/telegram.py`, with its
helper `.agent/notify/telegram_turn.py`), one switch, one credential store and one
message format.

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
✅ Задача завершена — <project> · <host>        (final turn)
💬 Промежуточный ответ — <project> · <host>     (any other turn)
🤖 <agent> · <model>
<session title, OpenCode only>

<answer of the turn>
```

```
⏳ Ожидает ввода — <project> · <host>
🤖 <agent> · <model>

<reason: permission, question with options, or idle prompt>
<command or resources as a code block>
```

- Every turn of the main session is still sent. Only the final turn has
  `✅ Задача завершена`. Interim turns start with `💬 Промежуточный ответ` and
  never contain `✅`; their body is rendered the same way.
- The `🤖` line names the main-session agent and the model of the last answer, for
  example `🤖 product-owner · claude-opus-5-5`. An unknown part is left out. When
  both are unknown, the line is left out and the message is still sent.
- A model id is shortened to its name: `openai/gpt-6-luna#high` → `gpt-6-luna`.

### Agent and model sources

All sources are local host data; there are no extra network calls.

| Host | Agent | Model |
| --- | --- | --- |
| Claude Code | `agent_type` of the hook input (main thread only, no `agent_id`), else the last `agent-setting` entry of the transcript, else `agent` in `.claude/settings.local.json`, then `.claude/settings.json` | `message.model` of the last main-thread assistant entry; `<synthetic>` and subagent entries are skipped |
| Codex | `agent_type` of the hook input, when present; the root session usually has none | `model` of the hook input |
| OpenCode | The plugin tracks `agent` from `session.created`, `session.agent.selected` and `session.step.started` | The plugin tracks `model` from the same events and `session.model.selected` |

### Final-turn rule

If the evidence is missing or unclear, the turn is interim: a missing mark is better
than a repeated one.

- **Claude Code.** The turn is interim when the `Stop` input lists `session_crons`
  or `background_tasks`, or when the transcript shows background work that the main
  thread launched and that has not finished. Launched work is an async `Agent`
  launch, a background Bash command, or a resumed agent (`SendMessage`). It finishes
  when the main thread receives its `<task-notification>` with a terminal status
  (`completed`, `failed`, `killed`, `stopped`, `cancelled`, `error`). A notification
  that is only queued does not count. A completion whose note says the agent still
  has `background work of its own still running` leaves the id pending. An empty
  `background_tasks` list from the host then settles that id, because the host has
  no work in flight. The empty list settles only these ids. Other ids stay pending
  until their own completion arrives, because the transcript also records launches
  that the list may leave out. Without a readable
  transcript, the turn is final only when the host sent an empty
  `background_tasks` list.
- **Codex.** The turn is final when the rollout (`transcript_path`) is readable and
  every child that the root opened with `spawn_agent` or `followup_task` sent a
  `FINAL_ANSWER` after its last open. Without a rollout (`--ephemeral`), every turn
  is interim.
- **OpenCode.** The plugin tracks child sessions. A root
  `session.execution.succeeded` is final when no child or grandchild session of
  that root is still running. The script trusts only `final: true` from the plugin.

Known limits:

- Older Claude Code releases do not send `background_tasks`. There, a subagent that
  sends the interim note and never reports again keeps every later turn of that
  session interim, so the rest of the session gets no `✅`.
- In Claude Code, an id that the main thread launched and that never gets a
  delivered terminal notification keeps the rest of that session without `✅`.
  Two examples: a session resumed after the host exited while agents were still
  running, or a killed task whose notification was suppressed. Start a new session
  to get `✅` again.
- Claude sessions with crons or `/loop` never get `✅`.
- Codex sessions without a rollout (`--ephemeral`) never get `✅`.
- The agent and model names are cut to 64 characters each.

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

- The script prints `{}` and exits 0 at once. A detached child process reads the
  transcript (up to 64 MiB, symlinks refused), builds the message and sends it, so
  neither the transcript scan nor Telegram latency blocks the agent.
- If `telegram_turn.py` is missing or fails, the message is still sent, as interim
  and without the `🤖` line.
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
  plain-text fallback, attachments, waiting events for all hosts). Fixtures in
  `tests/notify/fixtures/` cover the final-turn rule: a Claude task with async
  agents sends `Задача завершена` exactly once, on its last turn.
- `make blackbox` / `make blackbox-<host>` check that the real CLI delivers the
  final answer to a local fake API (`telegram_fired`).
- 2026-10-16: OpenCode 2.0.29 delivered both events through the plugin to a real
  bot and to the fake API; Claude Code and Codex `Stop` hooks fired in real blackbox
  runs.
