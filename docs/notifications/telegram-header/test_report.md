# TG-HDR — QA test report

Scope: [scope.md](scope.md) TG-1..TG-7. Design: [notes.md](notes.md). Implementation: [implementation_notes.md](implementation_notes.md).
Branch `feature/JEV-questions-rework`, uncommitted working tree. QA date: 2026-10-19.

## Recommendation

**Conditional GO.** All seven criteria pass with evidence. There are no blocking defects.

Condition: the product-owner accepts TG-D1 in writing as a known limit, or team-lead approves the small fix below before the commit. TG-D1 is a design-level, conservative behaviour: it never sends a repeated `✅`. But in a real SDLC session it can remove `✅` for all later tasks in that session. That reduces the main value of the feature.

## Risk summary

- 0 blocking defects.
- 1 major (P2): after one subagent completion with the "background work of its own still running" note, the Claude session never gets `✅` again (TG-D1).
- 1 minor (P3): `.agent/notify/__pycache__/` is created in user projects and is left behind after removal (TG-D2).
- 1 trivial (P4): one malformed transcript entry also drops the known agent and model (TG-D3).

## Gate evidence

| Command / check | Result |
|---|---|
| `make test-notify` | `Ran 24 tests … OK` |
| `make test` | exit 0. Rust unit 158 passed, cli 38 passed, e2e 13 passed. Content 20 OK, JEV hooks 86 OK, notify 24 OK. |
| `make lint` | exit 2 only because of `check-no-pycache`. These steps pass: `cargo fmt --check`, `clippy -D warnings`, `check-version-sync`, `lint_prompts --strict`, `lint_review_pipeline`, `sync_workflow_diagrams --check`, `build_docs_catalog --validate`. |
| `check-no-pycache` cause | Only `extensions/codex/hooks/jev/__pycache__/{questions,adapters,routing,api}.cpython-312.pyc` (directory time 11:40, from concurrent JEV QA). There is **no notify `__pycache__`** in the repository. I did not touch the JEV files. |
| File size | `telegram.py` 387 lines, `telegram_turn.py` 258 lines (both ≤ 400). |
| Function size (AST) | Only `markdown_html` (42 lines) is over 30. It is unchanged by this diff (pre-existing). |
| Network | `telegram_turn.py` has no `urllib`, `socket` or `http` import. The diff adds no new `urlopen`/`Request` call in `telegram.py` and no `fetch` in the plugin. One `sendMessage` per event, plus `sendDocument` for long bodies, as before (probe P09). |
| `make blackbox*` | Not run, as instructed. |

## Evidence per acceptance criterion

| AC | Verdict | Evidence |
|---|---|---|
| TG-1 header agent · model | PASS | Repo tests T1, T4, T6, T7. Probes: P10 (waiting header `⏳ … 🤖 product-owner · claude-opus-5-5`), P07 (`<synthetic>` and sidechain `agent-setting` skipped), P08 (HTML-special agent/model escaped in HTML, raw in plain fallback, for Claude and OpenCode), C05 (Codex `🤖 gpt-6-astra`). Unknown parts are omitted and the message is still sent (T7, P02). |
| TG-2 local sources, a fixture per host | PASS | Fixtures `claude_async_agents.jsonl` and `codex_rollout.jsonl`, plus OpenCode payload tests. No network code in the helper. Installed copy check: `agentic install --agent-os claude --enable-telegram` writes `.agent/notify/telegram_turn.py` with the marker line, and the Claude hooks call `telegram.py`. |
| TG-3 final-turn rule | PASS (with TG-D1) | Repo tests T1–T3, T5, T6. Probes: unknown-id notification is ignored (P05); resume makes an id pending again; an out-of-order notification does not clear a later launch; unknown status keeps the id pending; queue-only copies do not count; a sidechain notification does not clear a main-thread launch; uppercase status works (P06). `background_tasks` that is not a list falls back to the transcript (P12). Codex: re-open after `FINAL_ANSWER` → interim, namespaced `functions.spawn_agent`, dict arguments, bad JSON arguments → unkeyed → interim, `FINAL_ANSWER` from a child that was not opened is ignored, a non-final message type keeps the child open (C01–C04). OpenCode: only boolean `true` is final; `'true'`, `1`, `null` and missing → interim (O01). Node smoke run of the plugin: a running grandchild → `final:false`; after it fails → `final:true` with the new `session.agent.selected` value; a child that restarts → `final:false`. Waiting events carry the root agent/model. |
| TG-4 interim header | PASS | T1. P09: a long interim body sends `sendDocument` and then `sendMessage` that starts with `💬 <b>Промежуточный ответ</b> — …\n🤖 …\n<i>Полный ответ во вложении`. It has no `✅` and no `Задача завершена`, and it is ≤ 4096 characters. |
| TG-5 exactly one `✅`, the last one | PASS | T1 (4 stops over fixture slices; exactly one `Задача завершена`, and it is the last). The real-session replay below confirms the rule never gives a false `✅`. |
| TG-6 existing behaviour kept | PASS | T8, T9 and the full `make test`. P11: `stop_hook_active` sends nothing. H01: the hook-mode parent ran on a 60 MB transcript in 0.064 s with stdout `{}` and exit 0, so the scan runs only in the detached child. P04: a FIFO transcript path does not hang. P03: a symlinked transcript or settings file is refused in both `transcript_entries` and `transcript_reply`. The P02 error log has secrets redacted. P13: a 60 MB scan in the child takes 0.13 s. |
| TG-7 docs and changelog | PASS | `docs/notifications/README.md` shows the three headers, the `🤖` line, a source table, the rule per host and known limits. `README.md` has one bullet. `CHANGELOG.md` v1.4.0 has the Telegram header entry. Note: the known-limit text understates TG-D1 (see below). |

## Real-session replay (Claude, read-only)

Source: the real session transcript `37324278-….jsonl` (1182 lines at snapshot time). I used a read-only snapshot and deleted it after the run. No content is reproduced here. The replay ran `transcript_entries` → `main_thread` → `claude_pending` on the prefix before each main-thread `system/stop_hook_summary`. It compared the result with the next `system/turn_duration.pendingBackgroundAgentCount`, where an absent value means 0. The hook payload (`background_tasks`) is not stored in the transcript, so the replay covers the transcript part of the rule only.

| Result | Value |
|---|---|
| `stop_hook_summary` points | 22 |
| Points that get `✅` | **2** (points 1 and 15; the host count is 0 at both) |
| Same final/interim as the host count | 21 of 22 |
| Difference | Point 18: host count 0, rule pending 1 → interim. The id is a subagent whose two completions both have the interim note. |
| Count-only differences (both interim) | Points 19, 21, 22: rule 2, host 1. The extra id is the same subagent. |
| False `✅` | 0 |

The same subagent id stays pending at every later point, so the rest of this session can never get `✅` (TG-D1). A variant where an interim-note completion clears the id matches the host at 22 of 22 points (3 `✅`: points 1, 15, 18). But at point 20 the host counted 2 while the variant counted 1: the host re-activated that agent without a main-thread resume entry. So the variant is safe only together with the host's `background_tasks` list, which covers that case.

## Defect log

### TG-D1 — P2 Major — one interim-note completion removes `✅` for the rest of the Claude session

- **Business impact:** in a typical SDLC session, a subagent (for example a developer that leaves a background `make` running) completes with the interim note. From then on every coordinator turn is `💬`, including the final delivery reports of later tasks in the same session. The customer gets no "done" mark. That is the opposite failure of the original problem: it is safe, but it removes the value of the feature.
- **Repro (synthetic):** a transcript with `toolUseResult {isAsync:true,status:"async_launched",agentId:"a1"}` and then a delivered `<task-notification><task-id>a1</task-id><status>completed</status><note>… background work of its own still running</note>`. Payload `background_tasks: []`. Result: `final: False` on every later turn, even when the host reports nothing pending. **Repro (real):** replay point 18 above (host pending 0 → interim). All later points keep the id pending.
- **Expected (TG-3 wording):** the agent has a completion notification and the host lists no background work, so the turn is final.
- **Actual:** interim forever. The docs say "leaves the task without `✅`". In fact, it leaves all later tasks of the session without `✅`.
- **Suggested fix (team-lead decision):** when `background_tasks` is a list, an interim-note completion removes the id. The host list then covers a silent re-activation. Keep the current behaviour when `background_tasks` is absent. If the fix is deferred, update the known-limit text in `docs/notifications/README.md` to "the rest of the session", and record the product-owner's acceptance.

### TG-D2 — P3 Minor — `telegram_turn` import writes `__pycache__` into user projects

- **Repro:** run `agentic install --agent-os claude --areas software --specializations software.general --enable-telegram` in a scratch git repo. Run the hook once (`python3 .agent/notify/telegram.py --host claude --event stop --project-dir . --sync`). `.agent/notify/__pycache__/telegram_turn.cpython-312.pyc` appears. Then run the same install with `--disable-telegram`: both `.py` files are removed, but `.agent/notify/__pycache__/` stays.
- **Impact:** the user's `git status` shows an untracked `__pycache__`, and the uninstall is not clean. Before this change the notifier ran only as a script, so it wrote no bytecode.
- **Fix:** set `sys.dont_write_bytecode = True` before `import telegram_turn` in `telegram.py`, or remove `__pycache__` in the uninstall branch. The JEV runtime has the same import pattern. That is outside this scope, but it may explain the `jev/__pycache__` in the repository.

### TG-D3 — P4 Trivial — a malformed entry also drops the known agent and model

- **Repro:** a Claude transcript line with valid JSON `{"type":"user","message":"toolUseResult"}` (message is a string). `launched_ids` raises `AttributeError`. A Codex `agent_message` with integer `content` raises `TypeError`. `telegram.facts()` catches the error, logs `telegram turn facts failed: 'str' object has no attribute 'get'` with secrets redacted, and sends an interim message without the `🤖` line.
- **Impact:** it is conservative (no false `✅`, and the message is still sent). But known values are lost.
- **Fix:** guard `message`, `attachment` and `content` with `isinstance(..., dict/list)` checks.

## Observations (no defect)

- The symlink refusal checks the final path component only. A symlinked parent directory is followed, the same as the existing `transcript_reply`. This is acceptable for host-provided paths.
- OpenCode plugin logic has no automated TypeScript test (R5). My Node smoke run with a stubbed `@opencode/plugin` matched the design. A live `make blackbox-opencode` run is still open, after JEV-QR QA.
- When a Claude transcript cannot be read, the turn is final if `background_tasks` is `[]` (design §3.1 rule 3). The probe confirmed this. The `🤖` line then has no transcript-based agent or model.

## Probe artifacts (scratch, not in the repository)

- `/tmp/claude-1000/-home-e-isaev-test2/37324278-64aa-41c5-961d-deebbafe7649/scratchpad/probes/probe_tg.py`: 22 probes against the fake Bot API, all pass.
- `/tmp/claude-1000/-home-e-isaev-test2/37324278-64aa-41c5-961d-deebbafe7649/scratchpad/probes/replay.py`, `diag.py`, `variant.py`: real-session replay (counts only).

## Iteration 2 — re-verification of TG-D1..TG-D3 (2026-10-19)

### Recommendation

**GO.** TG-D1, TG-D2 and TG-D3 are fixed and verified. TG-1..TG-7 still pass. There are no open defects of severity P1–P3, so the product-owner acceptance condition from iteration 1 no longer applies.

### Gates

| Command / check | Result |
|---|---|
| `make test-notify` | `Ran 28 tests … OK` |
| `make test` | exit 0. Rust unit 158, cli 38 and e2e 13 passed. Content 20 OK, JEV hooks 86 OK, notify 28 OK. |
| `make lint` | **exit 0**, all steps including `check-no-pycache`. No `__pycache__` or `*.pyc` file is in the repository (outside `target/`). |
| Size | `telegram.py` 390 lines, `telegram_turn.py` 290 lines. Only `markdown_html` (42, unchanged) is over 30 lines. |
| Network | No network import in `telegram_turn.py`. |

### Probes (re-run, unchanged scripts)

All 22 probes in `probe_tg.py` pass. The changed outcomes:
- P02 (a user entry whose `message` is a string): no exception. The turn is `✅` with `🤖 product-owner · claude-opus-5-5`, and nothing goes to the debug log. **TG-D3 fixed.**
- C04 (a Codex `agent_message` with integer `content`): no exception, and the turn is interim (the child has no final answer). **TG-D3 fixed.**
- H02 (a script run with no `PYTHONDONTWRITEBYTECODE`): only `telegram.py` and `telegram_turn.py` are in the directory, with no `__pycache__`. **TG-D2 fixed.**

### Real-session replay (read-only, counts only, snapshot deleted after the run)

The transcript has grown to 1307 lines and 25 `stop_hook_summary` points. The replay calls `claude_final()` with three payload modes. The host value is the next `turn_duration.pendingBackgroundAgentCount`, where an absent value means 0.

| Payload mode | Points with ✅ | Agree with host | Differences |
|---|---|---|---|
| `background_tasks: []` at every point (the transcript alone must catch pending work) | **3** (points 1, 15, 18) | **25 / 25** | none |
| `background_tasks` sized to the host count (an approximation of the real payload) | 3 | 25 / 25 | none |
| `background_tasks` absent (older Claude) | 2 | 24 / 25 | point 18, the conservative interim, as designed |

No mode gives a false `✅`. Point 18 (host pending 0) now gets `✅`. The later points (19–25) are interim and agree with the host. **TG-D1 fixed.**

### D1 boundary (`d1_boundary.py`, 10 cases, 0 mismatches)

Base case: an async agent `a1` whose last terminal completion has the interim note.

| Case | final |
|---|---|
| `background_tasks` absent | False (the id stays pending) |
| `background_tasks: null` | False |
| `background_tasks: {}` | False |
| `background_tasks: []` | True |
| `background_tasks: [{id: a1}]` | False |
| resume of `a1` after the note, `[]` | False |
| a background Bash task still pending, `[]` | False (the host list does not clear non-interim ids) |
| a clean completion after the note, list absent | True |
| an interim note with non-terminal status `running`, `[]` | False |
| `session_crons` non-empty + `[]` | False |

### D2 boundary (real install)

Steps, in a scratch git repo, with `PYTHONDONTWRITEBYTECODE` unset:
1. Install with the current `target/debug/agentic` binary (built 11:57; the installed `telegram.py` contains `sys.dont_write_bytecode = True`), using `--agent-os claude --areas software --specializations software.general --enable-telegram`.
2. Run the Stop hook as Claude runs it (hook mode, `"$CLAUDE_PROJECT_DIR/.agent/notify/telegram.py"`): it prints `{}`. Then run it once in `--sync` mode, and wait 2 s for the detached child.

Results:
- `.agent/notify/` holds only `telegram.py` and `telegram_turn.py`.
- `find` finds no `__pycache__`, and `git status --untracked-files=all` lists no pycache entry.
- After `--disable-telegram`, both files are removed.

Observation (no defect): the empty `.agent/notify/` directory stays after removal. Git does not track empty directories, and the removal helper never deleted directories, so this behaviour is not new.

### Defect status

| ID | Severity | Status |
|---|---|---|
| TG-D1 | P2 | Fixed, verified (replay 25/25 with a host list; boundary cases). The conservative behaviour without `background_tasks` is documented in `docs/notifications/README.md` ("the rest of the session gets no ✅"). |
| TG-D2 | P3 | Fixed, verified (real install + hook run; repository test `test_script_run_leaves_no_bytecode_next_to_it`). |
| TG-D3 | P4 | Fixed, verified (P02, C04; repository test `test_malformed_entries_are_skipped_without_losing_facts`). |

Residual risks, unchanged: R1 (the Claude transcript format is internal), R3 (crons and `/loop` never get ✅), R4 (Codex `--ephemeral` never gets ✅), R5 (the OpenCode plugin has no automated TS test; a live `make blackbox-opencode` run is still open after JEV-QR QA).

Probe scripts (scratch): `/tmp/claude-1000/-home-e-isaev-test2/37324278-64aa-41c5-961d-deebbafe7649/scratchpad/probes/probe_tg.py`, `/tmp/claude-1000/-home-e-isaev-test2/37324278-64aa-41c5-961d-deebbafe7649/scratchpad/probes/replay2.py`, `/tmp/claude-1000/-home-e-isaev-test2/37324278-64aa-41c5-961d-deebbafe7649/scratchpad/probes/d1_boundary.py`.

### R5 live check (OpenCode, 2026-10-19, JEV-QR iteration 4 run)

Run: `make blackbox-opencode`, `.agentic-blackbox/20261019-121927/opencode/telegram.json` (fake Bot API).
OpenCode 2.0.29, session `openai/gpt-6-luna`, one harness approval follow-up.

- 2 `sendMessage` requests. Both start with `✅ <b>Задача завершена</b> — agentic-jev-blackbox-opencode-d9e7dr5d · OpenCode`.
  Both have the second line `🤖 build · gpt-6-luna`. The model string is shortened to the model id, and the agent is
  the real root agent (`build`).
- Each message closes a separate native turn that delivered: the first run, then the follow-up run. Each body reports
  delivery, and no subagent was still running. Two `✅` for two final turns follows TG-3. This is not a TG-5 violation:
  TG-5 counts interim turns inside one task.
- No interim turn happened, so `💬` was not observed live. It stays covered by T6 offline.
- `telegram_fired` is true. QR-D9 (relative `--run-dir`) is fixed in `scripts/blackbox_jev.py::run_root` and covered by
  `tests/jev/test_blackbox.py::RunRoot`.

R5 result: **pass** for the header (agent and model) and for the final mark. The live interim path stays unobserved
(residual, low).
