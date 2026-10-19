# TG-HDR — technical design (team-lead)

Scope: [scope.md](scope.md) (TG-1..TG-7). Status: approved for implementation by team-lead and product-owner (2026-10-19).

## 1. Evidence (local artifacts, 2026-10-19)

### 1.1 Claude Code (binary 2.1.303)

`Stop` hook input = base fields + `{stop_hook_active, last_assistant_message?, background_tasks?, session_crons?}`.

- **Base fields:** `session_id`, `transcript_path`, `cwd`, `prompt_id?`, `permission_mode?`, `agent_id?`, `agent_type?`, `effort?`. There is **no `model`** in the base input.
- **`agent_type`** is present inside a subagent (together with `agent_id`), or on the main thread of a `--agent` session (without `agent_id`).
- **`background_tasks[]`** lists in-flight background work. It is an empty array when nothing is in flight. Item shape: `{id, type, status, description, command?, agent_type?, ...}`.
- **`session_crons[]`** lists CronCreate / ScheduleWakeup / `/loop` tasks that will wake the session later.

Transcript shapes (main thread, `isSidechain: false`):

| Fact | JSONL shape |
|---|---|
| Agent setting | `{"type":"agent-setting","agentSetting":"product-owner"}`. Ignore `{"type":"agent-name",...}`: that is the session name. |
| Model | `type:"assistant"`, `message.model:"claude-opus-5-5"`. Skip values starting with `<` (for example `<synthetic>`). |
| Async agent launch | `type:"user"`, `toolUseResult:{"isAsync":true,"status":"async_launched","agentId":"a59c…",…}`. The text starts with `Async agent launched successfully.` and contains `agentId: <id>`. |
| Background Bash launch | `toolUseResult:{"backgroundTaskId":"bcsyxmng6",…}`. Text: `Command running in background with ID: bcsyxmng6.` |
| Agent resume (SendMessage) | `toolUseResult:{"success":true,"resumedAgentId":"a5d2…",…}`. The same id notifies again later. |
| Completion, delivered | One of two forms. (a) `type:"user"` with **string** `message.content` containing `<task-notification><task-id>ID</task-id>…<status>completed</status>…<note>…</note>`. (b) `type:"attachment"` with `attachment.type:"queued_command"`, `attachment.commandMode:"task-notification"`, and `attachment.prompt` holding the same block. |
| Completion, only queued | `{"type":"queue-operation","operation":"enqueue","content":"<task-notification>…"}`. **Not a completion.** |
| Interim completion | `<status>completed</status>` with a note that contains `background work of its own still running`. |
| Host ground truth | `system/turn_duration.pendingBackgroundAgentCount`. It is written after the Stop hook runs, so it is used for validation only. |

**Validation.** The §3.1 transcript rule was replayed against the real 1079-line session transcript.
- It matches the host's pending count at 18 of 19 turn ends.
- It gives ✅ only at the 2 real final turns.
- The one difference comes from the interim note: the rule keeps the turn interim, which is the conservative choice.

### 1.2 Codex (codex-cli 0.163.0)

- **`Stop` required fields:** `cwd, hook_event_name, last_assistant_message (nullable), model, permission_mode, session_id, stop_hook_active, transcript_path (nullable), turn_id`. There is no agent field.
- **Rollout (`transcript_path`):** the root `session_meta` has no `agent_role`.
- **Children:**
  - opened by a `response_item` `function_call` `name:"spawn_agent"` with args `{"task_name":"pm",...}`, or `name:"followup_task"` with args `{"target":"developer",...}`;
  - their result is a `response_item` `{"type":"agent_message","author":"/root/pm","recipient":"/root","content":[{"text":"Message Type: FINAL_ANSWER\n…"}]}`.
- **Observed:** the root turn always closed all its children before `task_complete`.

### 1.3 OpenCode (2.0.29, V2 events)

- `session.created {sessionID, parentID?, title?, agent?, model?}`.
- `session.agent.selected {agent}` and `session.model.selected {model}`.
- `session.step.started {sessionID, assistantMessageID, agent, model, …}`.
- `session.execution.started|succeeded|failed|interrupted {sessionID}`.
- `model` = `{id, providerID, variant?}`, or a string `provider/id#variant`.

## 2. Message format

| Kind | HTML first line | Plain first line |
|---|---|---|
| final | `✅ <b>Задача завершена</b> — {project} · {Host}` | `✅ Задача завершена — {project} · {Host}` |
| interim | `💬 <b>Промежуточный ответ</b> — {project} · {Host}` | `💬 Промежуточный ответ — {project} · {Host}` |
| waiting | `⏳ <b>Ожидает ввода</b> — {project} · {Host}` | `⏳ Ожидает ввода — {project} · {Host}` |

An optional second line, `🤖 <agent> · <model>`, follows the first line.
- An unknown part is omitted. When both parts are unknown, the line is omitted.
- Values are escaped with `esc()` in HTML.

Then come the existing title line (OpenCode), the attachment note and the body, all unchanged.

Model label normalization:
- dict → `id` or `modelID`;
- string → the part after the last `/`, with `#variant` removed. Example: `openai/gpt-6-luna#high` → `gpt-6-luna`.

An interim message never contains `✅` or `Задача завершена`.

## 3. Final-turn rule (conservative: missing or unreadable evidence → interim)

### 3.1 Claude

1. `session_crons` is a non-empty list → interim.
2. `background_tasks` is a non-empty list → interim.
3. Transcript pending set (`claude_pending`):
   - not empty → interim;
   - transcript unreadable → final only if `background_tasks` was a list, otherwise interim.
4. Otherwise → final.

**Pending set.** Read entries in file order. Skip `isSidechain: true` and the `api-request*` types.
- **Add:**
  - `toolUseResult.agentId` when `status == "async_launched"` or `isAsync` is true;
  - `toolUseResult.backgroundTaskId`;
  - `toolUseResult.resumedAgentId`;
  - text fallback when `toolUseResult` is missing: `Async agent launched` + `agentId: (\w+)`, and `Command running in background with ID: (\w+)`.
- **Remove** an id when all of these hold:
  - the `<task-notification>` block is in delivered form (user string content or a `queued_command` attachment prompt);
  - its status is one of `completed, failed, killed, stopped, cancelled, error`;
  - its note does not contain `background work of its own still running`.
- **Keep pending:** an interim-note block or an unknown status keeps the id pending.
- **Ignore:**
  - `queue-operation` entries;
  - notifications for ids that the main thread did not launch.

### 3.2 Codex

- **Final** when `transcript_path` is readable and every child that the root opened has a `FINAL_ANSWER` after its last open.
  - **Open:** a `spawn_agent` call (`task_name`) or a `followup_task` call (`target`). The key is the last path segment.
  - **Closed:** an `agent_message` whose `author` has that key as its last segment and whose text contains `Message Type: FINAL_ANSWER`.
- **Interim** when `transcript_path` is null or unreadable.

### 3.3 OpenCode (the plugin decides, the script trusts)

The plugin keeps four maps: `parents` (child → parent), `running` (a set), `agents` and `models`.
- `session.created` with `parentID` → set the parent and add the child to `running`.
- Child `execution.started` → add to `running`.
- Child `succeeded|failed|interrupted` → remove from `running`.
- `step.started`, `agent.selected`, `model.selected` and `created` → update `agents`/`models`; the last value wins.

On root `session.execution.succeeded`, the plugin sends `{session_id, title, last_assistant_message, agent, model, final}`.
- `final` is true when no running id has `rootOf(id) === root`. `rootOf` stops at depth 32.
- Waiting events add `agent`/`model` of `rootOf(sessionID)`.
- The script treats only `payload.final is True` as final for `--host opencode`.

### 3.4 Agent and model sources

| Host | Agent (first hit) | Model |
|---|---|---|
| Claude | 1) payload `agent_type` when `agent_id` is absent; 2) last transcript `agent-setting.agentSetting`; 3) `agent` in `.claude/settings.local.json`, then `.claude/settings.json` | last main-thread assistant `message.model`, skipping values that start with `<` |
| Codex | payload `agent_type` when `agent_id` is absent; otherwise omitted | payload `model` |
| OpenCode | payload `agent` | payload `model` (normalized) |

Waiting events use the same sources without the pending scan.

## 4. Code structure (≤30 lines per function, ≤400 lines per file, stdlib only)

### 4.1 New `extensions/codex/hooks/notify/telegram_turn.py` (~170 lines)

**Functions**
- `turn_facts(host, payload, project, read_json, with_final)` returns `{'agent','model','final'}`. `final` is False when `with_final` is False.
- `transcript_entries(raw_path, markers)` returns a list or `None`.
  - Streams the file line by line in binary mode.
  - Refuses symlinks and non-files.
  - Caps the read at `SCAN_LIMIT = 64 MiB`; over the cap it returns `None`.
  - Parses only lines that contain a marker and skips JSON errors.
  - Returns `None` on `OSError`.
- `model_label(value)`.
- Claude:
  - `claude_facts`, `claude_agent`, `claude_model`, `claude_final`, `claude_pending`;
  - `launched_ids(entry)`;
  - `delivered_notifications(entry)`;
  - `parse_notification(block)` → `(task_id, status, interim)`.
- Codex: `codex_facts(payload, with_final)` and `codex_open_children(entries)`.
- OpenCode: `opencode_facts(payload)`.

**Constants**
- `TERMINAL_STATUSES` and `INTERIM_NOTE`.
- `CLAUDE_MARKERS = (b'"assistant"', b'toolUseResult', b'<task-notification>', b'agent-setting')`.
- `CODEX_MARKERS = (b'spawn_agent', b'followup_task', b'FINAL_ANSWER')`.

Settings are read with the injected `read_json`.

### 4.2 `telegram.py` (341 → ~370 lines)

- **Guarded import.** `try: import telegram_turn` / `except ImportError: telegram_turn = None`. With no module the message is sent as interim, without the agent line.
- **Constant** `KINDS = {'final': ('✅','Задача завершена'), 'interim': ('💬','Промежуточный ответ'), 'waiting': ('⏳','Ожидает ввода')}`.
- **`header(kind, where, facts, title)`** → `(html, plain)`.
- **`build()`** is split into `stop_body` and `waiting_body`. `facts()` returns no agent, no model and `final: False` when the module is missing.
- **`main()`.** The hook-mode parent checks only `enabled` and the `stop_hook_active` skip, then detaches. `build()` runs only in the `--sync` child, so the transcript scan never blocks the agent. The `{}` output and exit 0 are unchanged.

### 4.3 `extensions/opencode/plugins/telegram-notification.ts`

- Replace the `children` set with the `parents` map.
- Add `running`, `agents`, `models` and `rootOf()`, as in §3.3.
- Payload keys: `agent`, `model` (raw), `final` (boolean).

### 4.4 `src/notify.rs`

- Add `TURN_REL = ".agent/notify/telegram_turn.py"` with an `include_str!`.
- Install it with `write_file_with_agentic_marker` and remove it with `legacy::remove_if_unmodified`, in the same branches as `telegram.py`.
- Extend the notify unit tests and `tests/cli.rs` (about lines 1211 and 1238) with `telegram_turn.py` assertions.

## 5. Test plan (`tests/notify/`, `make test-notify`)

Fixtures go in `tests/notify/fixtures/`. They are small hand-written JSONL files that copy the shapes in §1. Do not copy private transcripts.

| ID | Test | Covers |
|---|---|---|
| T1 | **Four stops over growing slices of `claude_async_agents.jsonl`**, with no `background_tasks` in the payload. (1) A and B launched → interim. (2) B delivered, A only queued → interim. (3) A completes with the interim note → interim. (4) A completes normally → final. Also include one notification for an id that was not launched (ignored). Assertions: 4 messages; exactly 1 contains `Задача завершена`, and it is the last; the others start with `💬` and contain no `✅`; every header has `🤖 product-owner · claude-opus-5-5`. | TG-1, TG-3–TG-5 |
| T2 | Non-empty `background_tasks` → interim. Non-empty `session_crons` → interim. `background_tasks: []` with no transcript → final. Neither source → interim. | TG-3 |
| T3 | `resumedAgentId` makes a completed agent pending again until its next notification. | TG-3 |
| T4 | Agent and model precedence. Payload `agent_type` wins. With `agent_id` present, the transcript is used. Settings fallback. `agent-name` is ignored. `<synthetic>` and sidechain models are skipped. | TG-1, TG-2 |
| T5 | Codex rollout fixture: `FINAL_ANSWER` present → final; missing → interim; `transcript_path: null` → interim. The header is `🤖 gpt-6-astra`. A waiting event shows the model. | TG-1–TG-3 |
| T6 | OpenCode: `agent: 'build'` + model dict + `final: true` → `✅`, `🤖 build · gpt-6-luna`, then the title. A model string `openai/gpt-6-luna#high` → `gpt-6-luna`. `final` missing or false → interim. | TG-1–TG-4 |
| T7 | Unknown agent and model → no `🤖` line, the message is still sent. `telegram_turn = None` → interim, exit 0. | TG-1 |
| T8 | Hook mode: `Popen` is called and `turn_facts` is not called in the parent. | TG-6 |
| T9 | The existing tests are kept with payload updates: Claude gets `background_tasks: []`, OpenCode gets `final: True`, and the expected headers include the `🤖` line. | TG-6 |
| T10 | Rust: `telegram_turn.py` is installed and removed together with `telegram.py`. | TG-6 |

Put the unit-level checks in a new `tests/notify/test_turn.py`. Keep the end-to-end tests in `test_telegram.py`.

## 6. Gates

1. `make test-notify`, `make test`, `make lint`.
2. `wc -l` ≤ 400 for both Python files, no function over 30 lines, and no new network calls.
3. Docs:
   - `docs/notifications/README.md`: the three headers, the `🤖` line, and the final-turn rule per host;
   - a short note in `README.md`;
   - an entry in the `CHANGELOG.md` v1.4.0 section.
4. Do not run `make blackbox*` while the JEV-QR QA run is active. Do not touch JEV files or `scripts/blackbox_jev.py`.

## 7. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | The Claude transcript format is internal. | The primary signal is `background_tasks`; the transcript is the fallback. Re-check on Claude upgrades. |
| R2 | A subagent that sends the interim note and never notifies again leaves the task without ✅. | Accepted by scope. Documented. |
| R3 | `session_crons` and `/loop` sessions never get ✅. | Accepted. Documented. |
| R4 | Codex `--ephemeral` (null `transcript_path`) never gets ✅. The root has no agent name. | Conservative default. The agent part is omitted. |
| R5 | The OpenCode plugin logic has no TypeScript unit test. | The Python contract is tested (T6). Live check with `make blackbox-opencode` after JEV-QR QA. |
| R6 | The blackbox `telegram_fired` check requires `Задача завершена`. | This is the intended end-to-end signal. The script is not changed here. |
| R7 | Large transcripts. | 64 MiB cap in the detached child. |
| R8 | Partial install. | Guarded import. The installer ships and removes both files. |
