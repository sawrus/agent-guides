# TG-HDR — implementation notes (developer)

Design: [notes.md](notes.md) §4–§6. Scope: [scope.md](scope.md) TG-1..TG-7. Branch `feature/JEV-questions-rework`, not committed.

## Changes per file

| File | Change |
|---|---|
| `extensions/codex/hooks/notify/telegram_turn.py` (new, 258 lines) | `turn_facts()` and the per-host rules of notes §3. Claude: `claude_facts/agent/model/final/pending`, `launched_ids`, `delivered_notifications`, `parse_notification`. Codex: `codex_facts`, `codex_open_children`, plus the helpers `codex_opened`/`codex_closed`. OpenCode: `opencode_facts`. Also `model_label`, and `transcript_entries`: it reads in binary mode, refuses symlinks and non-files, stops at 64 MiB, parses only marker lines and skips bad JSON. Stdlib only, no network. |
| `extensions/codex/hooks/notify/telegram.py` (341 → 387 lines) | Guarded `import telegram_turn`. Adds `KINDS`, `facts()` (falls back to interim, no agent line, when the module is missing or raises; the error is logged with secrets redacted), `header()`, `waiting_body()`, `stop_body()`, `skipped()`, `detach()`. `main()` hook mode checks only `enabled` and `stop_hook_active`, then detaches. `build()` runs only in the `--sync` child. |
| `extensions/opencode/plugins/telegram-notification.ts` | The `children` set is replaced by `parents`, `running`, `agents`, `models` and `rootOf()` (stops at depth 32). The plugin tracks `session.agent.selected`, `session.model.selected` and `session.step.started`. A child leaves `running` on `succeeded`, `failed` or `interrupted`. The stop payload adds `agent`, the raw `model`, and `final`. Waiting payloads add the root's `agent` and `model`. |
| `src/notify.rs` | `TURN_REL`/`TURN_SOURCE`/`TURN` (`include_str!`). It is written with `write_file_with_agentic_marker` in the same branch as `telegram.py`. It is removed with `legacy::remove_if_unmodified` in the same branch, which now loops over both files. Unit tests assert install and removal. |
| `tests/cli.rs` | Two `telegram_turn.py` assertions in `claude_jev_and_telegram_hooks_are_owned_and_removable`. |
| `tests/notify/test_turn.py` (new) | T2, T3, T4, T5 (unit), T6 (unit) and safety checks: symlink, directory, `None` path, broken JSON lines, scan cap. |
| `tests/notify/test_telegram.py` | T1, T5 (end to end), T6 (end to end), T7, T8. T9 payload updates: Claude `background_tasks: []`, OpenCode `final: True`, expected `🤖` lines. |
| `tests/notify/fixtures/claude_async_agents.jsonl`, `codex_rollout.jsonl` (new) | Small hand-written JSONL in the §1 shapes. They contain no private transcript content. |
| `docs/notifications/README.md` | The three headers, the `🤖` line, a source table per host, the final-turn rule per host, known limits, and the runtime note about the detached scan. |
| `README.md` | One bullet in "Telegram notifications". |
| `CHANGELOG.md` | One new v1.4.0 bullet, placed before the "Upgrade removes…" bullet. JEV-QR bullets are untouched. The version is already 1.4.0 (unreleased), so it is not bumped. |

## Test evidence (2026-10-19)

| Command | Result |
|---|---|
| `make test-notify` | `Ran 24 tests … OK` (9 in `test_turn.py`, 15 in `test_telegram.py`) |
| `make test` | exit 0. Rust unit 158 passed, cli 38 passed, e2e 13 passed. Content 20 OK, JEV hooks 86 OK, notify 24 OK. |
| `make lint` | `cargo fmt --check`, `clippy -D warnings`, `check-version-sync`, `lint_prompts --strict`, `lint_review_pipeline`, `sync_workflow_diagrams --check` and `build_docs_catalog --validate` pass. **`check-no-pycache` fails** on `extensions/codex/hooks/jev/__pycache__/*.pyc` (questions, adapters, routing, api; directory time 11:40). These are JEV files from the concurrent QA work, not from this change: the notify tests run with `PYTHONDONTWRITEBYTECODE=1`. I did not delete them because JEV files are off limits. |
| `wc -l` | `telegram.py` 387, `telegram_turn.py` 258 (both ≤ 400) |
| AST check, function length | No function in `telegram_turn.py` is over 30 lines. In `telegram.py` only `markdown_html` (42 lines) is over the limit. It was already that long, and this change did not touch it. |
| TS plugin | No Makefile target typechecks TypeScript. Informal checks: `node --experimental-strip-types --check` passes. A Node smoke run with a stubbed `@opencode/plugin` and a recording script covered root → child → grandchild. The first root stop sent `final:false` while the grandchild ran. The waiting event carried the root `agent`/`model`. After the grandchild was interrupted, the stop sent `final:true` with the new `session.model.selected` value. |
| Installed copy | `agentic install --agent-os claude --enable-telegram` into a scratch project writes both files. The marker line goes above the module docstring. The installed `telegram.py` imports `telegram_turn` and builds `✅ … 🤖 po`. |

`make blackbox*` was not run (JEV-QR QA is active).

## Deviations from the design and decisions not covered by it

1. **Codex item shape.** Rollout lines are `{"type":"response_item","payload":{…}}`. The design describes the inner item, so `codex_item()` reads `payload` and also accepts a bare item. The function name may have a namespace (`functions.spawn_agent`), so only the last `.` segment is compared.
2. **Unkeyed Codex child.** If a `spawn_agent`/`followup_task` call has no `task_name`/`target`, its child cannot be matched to its answer. It is recorded as `CODEX_UNKEYED`, so the turn stays interim ("uncertain → interim").
3. **Text fallback scope (Claude).** The text launch patterns apply only to `tool_result` blocks of `user` entries without a dict `toolUseResult`. Assistant prose that quotes "Command running in background with ID" is not counted.
4. **Interim note** is checked inside `<note>` only, as the design states.
5. **OpenCode agent value.** The plugin accepts a string, or an object with `name`/`id`. The event shape is not fully confirmed for `session.step.started`.
6. **`telegram_turn` failure.** The design covers a missing module. An exception raised inside `turn_facts` is also caught: the message goes out as interim, and the error goes to the debug log with secrets redacted.

## Known limitations

- R1: the Claude transcript format is internal. `background_tasks` is the primary signal. Re-check on Claude upgrades.
- R2/R3: a subagent that sends the interim note and never notifies again, or a session with `session_crons` or `/loop`, never gets `✅`.
- R4: Codex `--ephemeral` (null `transcript_path`) never gets `✅`. The Codex root has no agent name, so the line shows only the model.
- R5: the OpenCode plugin has no automated TypeScript test. The Python contract is tested (T6), and the smoke run above is informal. A live check with `make blackbox-opencode` remains after JEV-QR QA.
- R6: the blackbox `telegram_fired` check needs `Задача завершена`. A blackbox run whose last turn is interim (for example, a crons session) would now fail that check. This is intended.
- Partial upgrades: a project that has the new `telegram.py` but not `telegram_turn.py` sends every message as interim until reinstall.

## Iteration 2 — QA defects TG-D1..TG-D3 ([test_report.md](test_report.md))

### Fixes

| Defect | Change |
|---|---|
| TG-D1 (P2), interim note blocked `✅` for the rest of the session | The new `claude_pending_state(thread)` returns `(pending, still_running)`. `still_running` holds the pending ids whose last terminal completion had the interim note. A new launch or resume of an id takes it out of `still_running`, and a normal completion clears it. In `claude_final`, when `background_tasks` is a list, ids in `still_running` that are not in the host list (`host_task_ids`, the item `id`) are no longer pending. When `background_tasks` is absent or not a list (older Claude), the old conservative behaviour stays: the id stays pending. `claude_pending()` still returns the pending set. |
| TG-D2 (P3), `.agent/notify/__pycache__` in user projects | `telegram.py` sets `sys.dont_write_bytecode = True` before `import telegram_turn`. |
| TG-D3 (P4), a malformed entry dropped agent and model | `as_dict()` guards the Claude `message` and `attachment` fields. The new `message_texts()` guards the Codex `content` field (string, list or anything else). A malformed entry is now skipped, and the other facts are kept. |

### Decision: the host list clears only interim-note ids

The host `background_tasks` list does not clear other ids that the transcript shows as pending. Reasons:
- The transcript also records launches that the host list may leave out, for example background Bash commands and resumed agents.
- A pending id with no completion at all is real evidence of open work. The rule for unclear evidence still applies: the turn is interim.
- An interim-note id is different: the subagent already reported, and the transcript will hold no later event for that id. So the host is the only source that can settle it.
- QA saw the host re-activate such an agent without a resume entry in the main thread. Clearing the id is safe only because, in that case, the id is in the host list (or the list is not empty, so the turn is interim anyway).

QA's replay of this rule matched the host at 22 of 22 points.

### Tests added

- `test_turn.py::test_interim_note_is_settled_only_by_the_host_task_list`: `background_tasks: []` makes the turn final. A missing or non-list `background_tasks` keeps it interim. A resume after the note makes the id pending again. A background Bash launch is not cleared by the host list. A later normal completion clears the id even without the list.
- `test_turn.py::test_malformed_entries_are_skipped_without_losing_facts`: string, list and other non-dict `message`/`attachment` values in Claude entries; integer `content`, integer `arguments` and a string `payload` in Codex entries. Agent and model are kept, and no exception is raised.
- `test_telegram.py::test_interim_note_completion_does_not_block_a_later_done_mark`: end to end through the fake Bot API. Turn 1 launches `a1` (host lists it), turn 2 delivers an interim-note completion (host still lists it), and turn 3 starts the next task with `background_tasks: []`. The headers are `💬`, `💬`, `✅`, and every one has `🤖 product-owner · claude-opus-5-5`.
- `test_telegram.py::test_script_run_leaves_no_bytecode_next_to_it`: copies both files into a scratch `.agent/notify/` and runs the script as a subprocess, with every `PYTHON*` variable removed. It asserts that the message is delivered and that no `__pycache__` exists next to the script.
- Reverted-fix checks: I reverted each fix in turn on a scratch copy of the runtime. Each new test failed (D1: 2 failures, D2: 1 failure, D3: 1 error) and passes with the fix.

### Gate evidence (iteration 2)

| Command | Result |
|---|---|
| `make test-notify` | `Ran 28 tests … OK` |
| `make test` | exit 0. Rust unit 158, cli 38, e2e 13 passed. Content 20 OK, JEV hooks 86 OK, notify 28 OK. |
| `make lint` | exit 0, all steps including `check-no-pycache`. The JEV `__pycache__` from iteration 1 is gone; I did not remove it. |
| `wc -l` | `telegram.py` 390, `telegram_turn.py` 290 |
| Function length | No new function is over 30 lines. Only `markdown_html` (42 lines) is over the limit, and it is unchanged. |

### Docs

`docs/notifications/README.md` now describes how the host list settles interim-note ids. The known-limits list is now precise:
- On older Claude Code releases without `background_tasks`, an interim-note subagent that never reports again keeps **the rest of the session** without `✅`.
- Crons and `/loop` sessions never get `✅`.
- Codex `--ephemeral` sessions never get `✅`.

## Iteration 3 — team-lead NO-GO (P1-1) and P3 clean-ups

### Fixes

| Item | Change |
|---|---|
| P1-1, false `✅` after a text-only launch | `CLAUDE_MARKERS` now also has `b'Async agent launched'` and `b'Command running in background with ID'`. Before, a `user` tool_result line without `toolUseResult` matched no marker. The reader never parsed it, so the text fallback in `launched_ids` never ran. `b'tool_result'` is not added: it would parse almost every tool line for no gain. |
| P2-1, docs | The "Known limits" list in `docs/notifications/README.md` now says that any launched id with no delivered terminal notification keeps the rest of that Claude session without `✅`. Examples: a session resumed after the host exited with agents running, or a killed task whose notification was suppressed. The product-owner accepts this limit. |
| P3-1, dead code | `host_task_ids` is removed. At that point `background_tasks` is always `[]`, because a non-empty list returns interim earlier. The rule is now `pending -= still_running`. The comment and the README wording now say "an empty `background_tasks` list". |
| P3-2, label length | `telegram.header()` cuts the agent and the model to `LABEL_LIMIT = 64` characters each, before escaping. The README lists this limit. |
| P3-3, `read_json` | It now also refuses non-regular files (`not path.is_file()`), so a FIFO settings file cannot block the sender. |

### Tests added

| Test | What it checks |
|---|---|
| `test_turn.py::test_text_only_launch_lines_reach_the_pending_scan` | Reader-level: a JSONL file goes through `turn_facts`. There are two cases, an async agent text and a background Bash text, both without `toolUseResult`. Each is interim both without `background_tasks` and with `background_tasks: []`. |
| `test_telegram.py::test_agent_and_model_labels_are_capped` | 64-character cut, in HTML (escaped) and in plain text |
| `test_telegram.py::test_read_json_refuses_non_regular_files` | A FIFO returns the default within 5 s |

Reverted-fix checks on a scratch copy:
- Without the new markers, the reader test fails in both subtests.
- Without the cut, the label test fails.
- Without `is_file()`, the FIFO test fails, because the read blocks.

### Gate evidence (iteration 3)

| Command | Result |
|---|---|
| `make test-notify` | `Ran 31 tests … OK` |
| `make test` | exit 0. Rust unit 158, cli 38, e2e 13 passed. Content 20 OK, JEV hooks 86 OK, notify 31 OK. |
| `make lint` | exit 0 |
| `wc -l` | `telegram.py` 391, `telegram_turn.py` 290 |
| Function length | No new function is over 30 lines. Only `markdown_html` (42 lines) is over the limit, and it is unchanged. |

## Follow-ups (backlog, not done)

The product-owner deferred the team-lead review items P3-4 to P3-7 to the backlog:

| ID | Item |
|:---|:---|
| P3-4 | The symlink check and the open are separate steps in `transcript_entries`, a small TOCTOU window. Only the last path component is checked. Option: `os.open(..., O_NOFOLLOW)`. |
| P3-5 | Codex: two parallel `spawn_agent` calls with the same `task_name` share one key, so one `FINAL_ANSWER` closes both. It is not confirmed whether Codex allows duplicate names. |
| P3-6 | The OpenCode plugin maps (`parents`, `running`, `agents`, `models`) are never pruned, a slow leak in a long-lived server. A child with `session.created` but no execution event keeps its root interim. |
| P3-7 | `log()` writes `str(error)` to the local `.agentic/telegram-debug.log`. This may include transcript text; only the token and chat id are redacted. |
