# TG-HDR — Telegram notification header: agent, model, single "done" mark

## Problem statement

The Telegram `Stop` notification fires at the end of every main-session turn.

**Problem 1: the "done" mark is sent many times**
- With the SDLC workflow, the coordinator (`product-owner`) ends many turns while background subagents still run: launch an agent, wait, relay an interim result.
- Each of these turns sends `✅ Задача завершена`, so the customer gets the "done" mark several times per task.
- Only the coordinator's final report should carry it.

**Problem 2: the header does not say who answered**
- The header shows only `project · host`.
- The customer cannot see which agent and which model wrote the message.

Customer request (2026-10-19): «в заголовке кроме имени агента нужно писать название модели, и галочку "задача завершена" писать 1 раз — на последнее сообщение главного агента, который отчитывается в конце по итогу».

## Acceptance criteria

| ID | Criterion (testable) |
|:---|:---|
| TG-1 | Every `stop` and `waiting` message header contains the main-session agent name and the model that produced the last assistant message, for example `product-owner · claude-opus-5-5`. If a value is unknown, its part is left out; the message is still sent. |
| TG-2 | The agent and the model come from host data, without a network call. **Claude:** the session `agent` setting or the transcript, plus `message.model` of the last assistant entry. **Codex:** hook payload or session data. **OpenCode:** session or message `agent` / `modelID`. Each host has a unit test with a fixture. |
| TG-3 | `✅ Задача завершена` is sent only for a final turn. A turn is final when the main session ends it with no background work still pending: no launched subagent or background task without a completion notification. The rule is designed by team-lead per host. |
| TG-4 | A non-final turn sends a message without `✅` and without «Задача завершена», with a distinct header, for example `💬 Промежуточный ответ`. Its body and Markdown rendering are unchanged. |
| TG-5 | In a task with N interim turns and one final turn, the fake Bot API receives exactly one message containing `Задача завершена`, and it is the last one. Tested for Claude with a transcript fixture that has an async agent launch and its later completion notification. |
| TG-6 | Existing behaviour is kept: redaction of token and chat id, long-body document attachment, HTML → plain-text fallback, `stop_hook_active` skip, detached send, exit 0 with `{}`, enable/disable settings. `make test` passes, including `tests/notify`. |
| TG-7 | `README.md` / docs describe the new header and the final-turn rule; `CHANGELOG.md` v1.4.0 has an entry. |

## Constraints

- Runtime is `extensions/codex/hooks/notify/telegram.py` (341 lines, limit ~400) plus the OpenCode plugin `extensions/opencode/plugins/telegram-notification.ts`.
- Use stdlib only, never block the agent, and send no extra Telegram calls.
- If detection is uncertain, send no `✅`. A missing mark is better than a repeated one.

## Non-goals

- No change to the `waiting` trigger rules.
- No message suppression: interim turns are still sent.
- No notifications for subagents (`SubagentStop`).

## Delivery

- Same working tree and branch as JEV-QR (`feature/JEV-questions-rework`); it will be a separate commit.
- SDLC: team-lead design → developer → qa → product-owner acceptance.
