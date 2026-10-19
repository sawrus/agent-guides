# TG-HDR — Delivery report

**Acceptance decision (product-owner, 2026-10-19): APPROVED.**
- TG-1 to TG-7 pass on the evidence in `test_report.md` (iterations 1–2) and the team-lead re-review of iteration 3.
- One check is still open: the live OpenCode run. It is planned together with the JEV-QR AC-19 OpenCode run (see Open items).

**Sign-offs**
- QA: GO (iteration 2).
- team-lead: technical GO (iteration 3, after the P1-1 fix).

**Branch:** `feature/JEV-questions-rework`. Not committed yet; this will be a separate commit from JEV-QR.

## What shipped

**Headers**
- Every Telegram notification has a second header line: `🤖 <agent> · <model>`.
  - Each part is left out when it is unknown.
  - Each label is cut to 64 characters.
- There are three header kinds:
  - `✅ Задача завершена` for the final turn;
  - `💬 Промежуточный ответ` for an interim turn;
  - `⏳ Ожидает ввода` for a turn that waits for the user.

**Final-turn rule, per host.** `✅` is sent only with positive evidence that no background work is pending:
- **Claude:** `background_tasks` / `session_crons` from the host, plus a scan of the transcript for launches and delivered completions.
- **Codex:** every spawned child has returned `FINAL_ANSWER`.
- **OpenCode:** the plugin tracks child sessions and passes `final`.

**Runtime**
- New helper `telegram_turn.py`, installed and removed together with `telegram.py`.
- The message is built only in the detached child, so the agent never waits.
- No bytecode cache is written in user projects.
- Malformed transcript entries are skipped.

## Evidence

| Check | Result |
|:---|:---|
| `make test-notify` | 31 OK (iteration 3) |
| `make test` / `make lint` | exit 0 (developer, iteration 3) |
| QA probes | 22 adversarial probes pass (iteration 2) |
| Replay on a real session | 25 stop points: ✅ at 3 real final turns, agrees with the host at 25/25, no false ✅ |
| team-lead P1-1 probe | a text-only launch now stays interim |

## Accepted limits (product-owner, written)

**P2-1.** A launched id that never receives a delivered terminal notification keeps the rest of that Claude session without `✅`.
- Example: a session resumed after the host exited while agents ran.
- Example: a killed task whose notification was suppressed.
- Accepted because the failure is in the safe direction: a lost mark, never a repeated one.
- Workaround: start a new session.

**No ✅ by design.** These cases never get `✅`:
- sessions with crons or `/loop`;
- Codex `--ephemeral`;
- older Claude versions without `background_tasks`, after an interim-note completion.

## Open items

| ID | Item | Owner |
|:---|:---|:---|
| R5 | Live check of the OpenCode plugin (`final`, agent, model) in the next `make blackbox-opencode` run (JEV-QR AC-19) | QA |
| P3-4..P3-7 | Backlog items, listed in `implementation_notes.md` | team-lead |
| R1 | The Claude transcript format is internal; re-check it on Claude upgrades | team-lead |

## Rollout and rollback

- **Rollout:** reinstall `agentic` in a project. The installer writes `.agent/notify/telegram.py` and `telegram_turn.py`.
- **Rollback:**
  - reinstall from `main`;
  - or disable notifications with `--disable-telegram`.
- **Missing helper:** if `telegram_turn.py` is missing, messages are still sent, but as interim and without the agent line.
