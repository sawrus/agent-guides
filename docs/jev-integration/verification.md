# Native verification, 2026-10-14

## Scope and outcomes

Real installed Codex and OpenCode V2 received the exact prompt
`разработай калькулятор` in separate temporary Git projects created by Agentic.
Installation selected `software.backend` and `software.general` with JEV enabled.
OpenCode tests used only OpenAI models. Codex hooks were reviewed and trusted in
the native TUI; no sandbox or hook-trust bypass was used.

Both environments selected and loaded `development-cycle-workflow`. Native
observations confirmed model application, and independent probes executed the
delivered calculator APIs for addition, subtraction, multiplication, division
and division by zero. Agent-authored acceptance JSON was not used as proof.

| Environment | Confirmed routing | Evidence limits |
| --- | --- | --- |
| Codex 0.161.0 | Real JEV decisions applied `gpt-6-luna` to developer and QA in the initial run; developer and memory curator in the subsequent verification | Other assignments fell back below confidence 0.9. Exact encrypted assignments remained unavailable. |
| OpenCode V2 | Real JEV decisions applied `openai/gpt-5.5-fast` through native `subagent.model` | Catalog prices were unknown. Some other events retained native models; this is not proof of savings for every role. |

OpenCode routing uses production rules, without a special test routing override.
Candidates come from installed role defaults and the available host catalog.
Explicit tool/Markdown/local configuration pins remain authoritative.

Recorded JEV costs for representative runs were $0.003619 for Codex and
$0.006819 for OpenCode. These are decision-service costs reported by the gateway,
not coding-model costs or measured savings. The shared conservative budget ledger
remained below the agreed $5. No official paid quota was used; official API
contracts were checked offline.

Local cleansed artifacts are under `.agentic-blackbox/20261014-113837/` for Codex
and `.agentic-blackbox/20261014-120201/` for OpenCode. They are ignored and are not
part of a clone. `project.json` identifies each retained temporary project.
Subsequent verification uses only the session in its current native trace;
previous successful sessions cannot pass a new failed run.

## Review handoff

The Codex verification confirmed that instruction reviewer consumed the current
task's JEV decision records and returned concrete followups with source, target,
owner and completion criteria. Encrypted assignments were preserved byte for byte;
the journal path was delivered through native `SubagentStart` context.

The subsequent OpenCode run also confirmed task-scoped Q/A review. OpenCode
receives the packet directly in its reviewer assignment, with
an absolute path to the full packet and referenced records. Inline context is
bounded to 64 KiB. This avoids relying on ordinary search, which skips ignored
journals, or on coordinator claims that the records are absent. Recommendations
are advisory and do not authorize edits to instructions or exceptions to customer
approval requirements.

Browser interaction and external release were not independently demonstrated.
The acceptance probe verifies calculator arithmetic, not screenshots, viewport
layout, deployment or a merged PR in the temporary projects.

## Offline checks

All checks run through Makefile targets. Unit/CLI/content/hook tests cover native
contracts, default model pools, pins, low confidence, timeout/failure, disabled
integration, redaction, retention, event deduplication, permission boundaries,
foreign hooks, edited assets and migration. SDK typechecking uses pinned OpenCode
2.0.28. Rust coverage passed the 80% line gate (82.83%).

Permission checks include outside paths, secret files, deletion, patch move
destinations, symlink escapes, shell working directories and indirect shell file
reads. Independent calculator probes reject broken arithmetic and self-reported
acceptance. A run lock prevents overlapping tests from corrupting a shared trace.

# Native verification, 2026-10-16 (Claude Code)

Real Claude Code 2.1.301 received the exact prompt `разработай калькулятор` in a
temporary Git project installed by Agentic 1.4.0 (`software.backend` +
`software.general`, JEV and Telegram hooks enabled, coordinator model `sonnet`).
The run used `make blackbox-claude`. Cleansed artifacts are in
`.agentic-blackbox/20261016-165654/claude/`.

| Check | Result | Evidence |
| --- | --- | --- |
| Native exit | passed | Every stream-json `result` event is `success` |
| JEV workflow selection | passed | JEV selected `development-cycle-workflow`; the agent read the file (PostToolUse) |
| Model routing | passed | `haiku` was requested for the Explore subagent and observed as `claude-haiku-5-5` (SubagentStop transcript) |
| Agents / commands / skills | passed | The `init` event lists all nine roles, `/develop-feature` and the installed skills |
| Rules and imports | passed | `InstructionsLoaded` recorded `.claude/rules/*.md`, `AGENTS.md` and `MEMORY.md` (via `@` imports) |
| Telegram `Stop` hook | passed | The local fake Bot API received `✅ Задача завершена — …` with the final answer |
| Calculator | passed | Independent probe: `calculator/…:evaluate`, the four operations and division by zero |
| Post-task review | passed | `instruction-reviewer` and `memory-curator` ran once; reports were saved in `.reviews/CALC-001/`; a JEV review packet was produced |

Limitations:

- Most spawn decisions (team-lead, developer, qa, memory-curator) fell back to
  native models below confidence 0.9.
- `instruction-reviewer` was routed to `haiku` by the configured lightweight rule,
  without a paid call.
- All 14 permission evaluations fell back (`low_confidence`), so automatic
  approval was not exercised in this run.
- The gateway reported no cost (`jev_reported_cost_usd: 0`). Coding-model cost
  reported by Claude was $1.56.
- The coordinator first stopped to request approval for new root files, as the
  project rules require. The run then sent its single bounded approval follow-up
  through `--resume`.

# Native verification, 2026-10-16 (OpenCode and Codex, Agentic 1.4.0)

| Host | Run | Outcome |
| --- | --- | --- |
| OpenCode 2.0.29, `openai/gpt-6-luna` | `.agentic-blackbox/20261016-233233` | JEV selected `development-cycle-workflow`; the agent read it and ran PO → `pm` → `team-lead` → `developer` → `qa` → `instruction-reviewer` + `memory-curator` with the 1.4.0 names, after one approval follow-up. The independent probe verified `docs/calculator/app.js:calculate` (typographic operators). JEV returned `no_decision` for all ten spawns, so `model_applied_to_subagent` failed. |
| Codex 0.163.0 | `.agentic-blackbox/20261016-232317` | First attempts: JEV selected the workflow and the Telegram `Stop` hook delivered, but commands failed with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted` (the host sets `kernel.apparmor_restrict_unprivileged_userns=1`, so the `workspace-write` sandbox cannot start). Rerun on 2026-10-17 with `BLACKBOX_CODEX_SANDBOX=danger-full-access`, after one approval follow-up: **passed all six checks**. JEV applied `gpt-6-luna` to PO, `pm`, `team-lead`, `developer`, `qa`, `instruction-reviewer` (review packet routed) and `memory-curator`; one `team-lead` spawn fell back and ran on the session model `gpt-6-astra`. The probe verified `calculator/src/calculator.js` (keypad state API, typographic operators). Both permission evaluations fell back. |

`openai/gpt-5.5` is no longer served for ChatGPT-account OAuth in OpenCode, so the
blackbox default moved to `openai/gpt-6-luna`. Hooks were trusted manually in Codex
`/hooks` before the run.

Telegram (real bot and fake API, outside the blackbox target): OpenCode V2 did not
load the 1.3.0 plugin (`Plugin must export a default definition`). The 1.4.0 plugin
uses `Plugin.define` and delivered both `⏳ Ожидает ввода` (`permission.asked`) and
`✅ Задача завершена` with Telegram HTML formatting.
