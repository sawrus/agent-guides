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

# Native verification, 2026-10-17 (Claude Code, opus session, Agentic 1.4.0)

A manual Claude session in an installed project (session model `opus`) showed
that 6 of 7 spawns fell back and inherited `opus`. Two hook defects caused this:

- Claude Code delivers subagent hand-backs (`<agent-message …>`) and task
  notifications through `UserPromptSubmit`. The hook treated each one as a new
  task and replaced the original request, so JEV judged spawns against a
  subagent report.
- `AskUserQuestion` was sent to JEV as a permission request.

After the fix, `BLACKBOX_CLAUDE_MODEL=opus make blackbox-claude` with Claude Code
2.1.302 passed all ten checks (`.agentic-blackbox/20261017-232709`). Every spawn
decision saw the original request `разработай калькулятор`, and the hook read
`default_model: opus` from the session.

| Role | JEV answer | Applied | Observed |
| --- | --- | --- | --- |
| Explore (exploration) | haiku 0.98 | haiku (JEV) | `claude-haiku-5-5` |
| team-lead (design) | opus 0.37 | opus (profile default) | `claude-opus-5-5` |
| developer | haiku 0.40 | sonnet (profile default) | `claude-sonnet-5-5` |
| qa | haiku 0.31 | sonnet (profile default) | `claude-sonnet-5-5` |
| team-lead (review) | haiku 0.64 | opus (profile default) | `claude-opus-5-5` |
| instruction-reviewer | — | haiku (lightweight reviewer rule) | `claude-haiku-5-5` |
| memory-curator | haiku 0.85 | haiku (profile default) | `claude-haiku-5-5` |

Limits:

- JEV answered above the 0.9 threshold only for exploration. The other spawns
  used the Claude profile role defaults, not JEV routing; the blackbox counts only
  `evaluated` answers as JEV routing.
- All 16 permission evaluations fell back below 0.9 (10 leaned `allow`, but only
  one request was inside the automatic allow boundary). Claude's native permission
  handling decided them.

# Native verification, 2026-10-19 (JEV questions rework, Agentic 1.4.0)

Prompt `разработай калькулятор`, areas `software.backend` + `software.general`. JEV ledger
`committed_usd` 1.94 → 2.12 (+$0.18; the endpoint returned `cost_usd: null`, so the ledger counts a
conservative reservation per call). Full evidence: `questions-rework/test_report.md`.

| Host | Run | Status | Questions (workflow / model / permission) | Applied vs fallback |
| --- | --- | --- | --- | --- |
| Codex 0.163.0, `danger-full-access` | `.agentic-blackbox/20261019-003813` | blocked: no JEV hook event within 60 s; project hooks are not trusted | 0 / 0 / 0 | — |
| OpenCode 2.0.29, `openai/gpt-6-luna` | `.agentic-blackbox/20261019-003942` | failed `model_applied_to_subagent`; other 5 checks pass | 2 / 0 / 0 | 1 / 1 |
| Claude Code 2.1.302, session `sonnet` | `.agentic-blackbox/20261019-004345` | passed 10/10 | 1 / 3 / 3 | 2 / 5 (baseline 2 / 9) |

**Codex.** The manual step is for the user: in `/tmp/agentic-jev-blackbox-codex-cbdhtpj2` run `codex`, then
`/hooks` and trust the project hooks. Then rerun
`BLACKBOX_CODEX_SANDBOX=danger-full-access BLACKBOX_ARGS="--run-dir .agentic-blackbox/20261019-003813" make blackbox-codex`.

**OpenCode.**

- Workflow: `development-cycle-workflow` at 1.0 (`jev_applied`), and the agent read it.
- The approval follow-up prompt got `clarify` at 0.47 (`low_confidence`, native).
- All 10 spawns returned `fallback/no_tier_routing` with `model_source: none`. The default install pins no agent
  models and writes empty profile defaults, so the plugin sends `models: []` and `role_default: null`. No model
  question is sent.
- Observed models: `openai/gpt-6-luna` for all 7 observations. The `explore` observation has `agent: null` and
  `native_agent_type: explore`.

**Claude.**

| Role / question | JEV answer | Outcome, reason | model_source | Applied | Observed |
| --- | --- | --- | --- | --- | --- |
| workflow | development-cycle-workflow 1.00 | jev_applied | — | — | workflow read |
| team-lead | balanced 0.80 | role_default_applied, `low_confidence` | role_default | opus | `claude-opus-5-5` |
| developer | balanced 0.92 | jev_applied | jev_tier | sonnet | `claude-sonnet-5-5` |
| qa | balanced 0.53 | role_default_applied, `low_confidence` | role_default | sonnet | `claude-sonnet-5-5` |
| 3 × permission (Bash) | deny 0.20 / 0.22 / 0.28 | native, `low_confidence` | — | — | — |

- The developer ran on sonnet, not opus. No spawn inherited the session model.
- Permission state held only command metadata and the installed role label.

AC-1 runtime check: `request.questions` and the hook-injected context name neither `calculator` nor `CRUD` on
OpenCode or Claude (state excluded, D2). Paid R&D (`JEV_RND_SUITE=questions`) did not run: there is no
`JEV_API_KEY` for the hosted endpoint.

## Rerun after Scope change 1, 2026-10-19 (iteration 2)

JEV ledger `committed_usd` 2.12 → 3.18. Of the +$1.06, R&D used $0.80 for 40 calls, OpenCode $0.04 and Claude $0.22.
The endpoint reports no cost, so the ledger books $0.02 per call.

R&D questions suite through the hook client (`api.typesafe.ai`):
- workflow_routing 12/12 and model_tier 8/8, in both option orders.
- These tier answers agreed but scored below 0.9: pagination 0.75 (reversed), architecture 0.79/0.80,
  small program 0.89 (reversed), sessions 0.53/0.53.

| Host | Run | Status | Questions (workflow / model / permission) | Applied |
| --- | --- | --- | --- | --- |
| Codex 0.163.0 | `.agentic-blackbox/20261019-003813` | still blocked on `/hooks` trust; not rerun | — | — |
| OpenCode 2.0.29, `openai/gpt-6-luna` | `.agentic-blackbox/20261019-010215` | failed `model_applied_to_subagent` and `calculator_verified` | 2 / 0 / 0 | 1 / 2 |
| Claude Code 2.1.302, session `sonnet` | `.agentic-blackbox/20261019-010517` | failed `model_applied_to_subagent` | 2 / 8 / 1 | 3 / 11 |

**OpenCode.**
- Workflow `development-cycle-workflow` at 1.0. The follow-up prompt got 0.50 (fallback).
- All 12 spawns returned `no_tier_routing` with `model_source: none`. This is the deferred QR-D2 (no role models).
- Observed model: `openai/gpt-6-luna` for every observation.
- The calculator was a DOM-only script with no public function, so the probe could not verify it.

**Claude.**
- JEV applied two spawns: Explore `fast` 1.00 → haiku (observed `claude-haiku-5-5`) and developer `balanced` 0.97 → sonnet
  (observed `claude-sonnet-5-5`; not opus).
- team-lead (×3, 0.51–0.73), qa (×2, 0.33/0.47) and memory-curator (0.63) fell back on `low_confidence` to the
  role defaults opus / sonnet / haiku, and those are the models observed.
- The instruction-reviewer ran on the lightweight `review_model` haiku.
- Permissions: 28 Bash events with `auto_allow_eligible: false` became `fallback/not_auto_allow_eligible` with no JEV
  call. One eligible `Write` was asked (allow 0.69, `low_confidence`). Claude decided all of them natively.
- `model_applied_to_subagent` fails for two reasons, not because of routing:
  - The spawn record keeps `agent: "Explore"`, while the observation has `agent: null` +
    `native_agent_type: "Explore"` (QR-D6).
  - The developer spawn came after the approval follow-up, which opened a new task that `verify` does not count (QR-D7).

AC-1 runtime check: 0 hits in `request.questions` or injected context on both hosts.

## Offline re-verification after iteration 3, 2026-10-19

The recorded runs were rechecked with `BLACKBOX_ARGS="--verify-only --run-dir …"`. No model requests were sent, and
the ledger stays at 3.18.

| Host | Run | Result |
| --- | --- | --- |
| Claude | `.agentic-blackbox/20261019-010517` | **passed 10/10**. `model_applied_to_subagent` is now true: the Explore spawn (JEV `fast` → haiku) pairs with the `claude-haiku-5-5` observation by `native_agent_type` (QR-D6 fix). The developer sonnet spawn is still outside the counted task because it came after the follow-up (QR-D7). |
| OpenCode | `.agentic-blackbox/20261019-010215` | unchanged: `model_applied_to_subagent` false (no role models, QR-D2 deferred) and `calculator_verified` false (no public API). |
| Codex | `.agentic-blackbox/20261019-003813` | still blocked: trust the hooks in `codex` → `/hooks`, then rerun with `--run-dir`. |

## Codex run and OpenCode model-routing check, 2026-10-19 (iteration 3)

JEV ledger `committed_usd` 3.18 → 3.32 (+$0.14, 158 → 165 calls). Codex used +$0.10 (5 calls) and OpenCode +$0.04
(2 calls). The endpoint reports no cost, so the ledger books $0.02 per call. Full evidence: `questions-rework/test_report.md`.

| Host | Run | Status | Questions (workflow / model / permission) | Applied |
| --- | --- | --- | --- | --- |
| Codex 0.163.0, `danger-full-access`, session `gpt-6-astra` | `.agentic-blackbox/20261019-003813` | failed `model_applied_to_subagent` (no confident tier) and `telegram_fired` (harness, QR-D9); 4 other checks pass, calculator verified | 1 / 4 / 0 | 1 / 5 |
| OpenCode 2.0.29, `openai/gpt-6-luna`, `AGENTIC_OPENCODE_PROFILE=openai` | `.agentic-blackbox/20261019-114054` | failed `model_applied_to_subagent` (no model question) and `calculator_verified` (no public API) | 2 / 0 / 0 | 1 / 2 |

**Codex.**

- Runtime: the trusted temp project had stale `api.py`, `hook.py` and `questions.py` from before iteration 2. The
  `--run-dir` rerun reinstalls through `install_project`. The new `hooks.json` was byte-identical, so the trusted hook
  hashes in `~/.codex/config.toml` still matched. After the reinstall, all five runtime files equal the current source.
- Workflow: `development-cycle-workflow` at 0.99, `jev_applied`, and the agent read it. No follow-up was needed.
- Candidates on every spawn were `fast gpt-6-luna`, `balanced gpt-6.1-sol` and `frontier gpt-6-astra`
  (`cost_source: tier_order`, `relative_cost` 1/2/3, `quota: unknown`, no `default_model`). These match
  `extensions/codex/model-tiers.json`.
- Codex encrypts the spawn assignment. State carried `assignment_unavailable: true` and a placeholder text.

| Spawn | JEV answer | Outcome, reason | Tier / model_source | Model | Observed |
| --- | --- | --- | --- | --- | --- |
| product-owner | clarify 0.40 | role_default_applied, `low_confidence` | balanced / role_default | gpt-6.1-sol | gpt-6.1-sol |
| team-lead | clarify 0.47 | role_default_applied, `low_confidence` | balanced / role_default | gpt-6.1-sol | gpt-6.1-sol |
| developer | clarify 0.52 | role_default_applied, `low_confidence` | balanced / role_default | gpt-6.1-sol | gpt-6.1-sol |
| qa | clarify 0.60 | native, `low_confidence` | — / none | — | gpt-6-astra |

- D6 is observed. The qa default `gpt-6-terra` is not a candidate, so `role_default` is `null`. qa then inherited
  the session model `gpt-6-astra`, which is the most expensive tier.
- Permissions: there were no `PermissionRequest` events under `danger-full-access`.
- `model_applied_to_subagent` is false by design: role-default fallbacks keep `status: fallback`. No spawn got a
  confident tier.
- `telegram_fired` is false because of the harness (QR-D9). A relative `--run-dir` makes `AGENTIC_CONFIG_DIR`
  relative, and the Stop hook resolves it from the project cwd. `.agentic/telegram-debug.log` says
  "telegram credentials missing".
- AC-1: 0 hits in the 5 `request.questions` and in the 4 rebuilt injected contexts.

**OpenCode model routing: what is and is not verified.**

- Default install (runs `20261019-003942`, `20261019-010215`): the plugin sent `models: []` and `role_default: null`,
  with no `prices`. Every spawn was `fallback/no_tier_routing`, `model_source: none`, and no model question was sent.
- With `AGENTIC_OPENCODE_PROFILE=openai` (installer option, no product change), the run gave the following:
  - `opencode-profile-defaults.json` and `.opencode/opencode.json` carry the profile role models.
  - The plugin pool held only `openai/gpt-6-luna`. Two reasons:
    - `product-owner`, `team-lead` and `devops-engineer` use the bare `gpt-6.1-sol`, with no `openai/` prefix.
    - `developer` uses `openai/gpt-6-terra`, which is not in the OpenCode catalog.
  - All 17 spawns were `routed/single_eligible_model` → `openai/gpt-6-luna` (`model_source: single_eligible`).
  - No model question was sent. All 10 observations show `openai/gpt-6-luna`.
- Prices: the plugin sent `prices: []` for `openai/gpt-6-luna` (`ctx.model.list()` `cost`). OpenCode authenticates
  OpenAI by `oauth` (subscription), and every trace step reports `"cost": 0`. The models.dev cache
  (`~/.cache/opencode/models.json`) has dict prices for luna, 6.1-sol and astra, but the runtime model list does not
  expose them to the plugin.
- `routing.price([])` is `None`. So under AC-7, OpenAI-on-OpenCode gives **no tier routing even with two or more role
  models**; the hook falls back to the role default.
- Verified: tier derivation from prices, offline only (unit tests and a probe with catalog prices: luna fast,
  6.1-sol balanced, astra frontier). Also verified: the single-eligible rule and the pass-through of the plugin payload.
- Not verified at runtime on OpenCode: a model question, tier → model mapping, and the `role_default` fallback with
  `model_source: role_default`.

## OpenCode model routing after the QR-D2 fix, 2026-10-19 (iteration 4)

The ledger went from `committed_usd` 3.32 to 3.56 (+$0.24, 165 → 177 calls). That is 12 calls: 2 workflow questions and
10 model questions. The ceiling was $3.92, and there was no re-run. The run was `make blackbox-opencode` on a default
install, with no `AGENTIC_OPENCODE_PROFILE` (OpenCode 2.0.29, `openai/gpt-6-luna`, OpenAI login `oauth`). Full evidence:
`questions-rework/test_report.md`.

| Host | Run | Status | Questions (workflow / model / permission) | Applied |
| --- | --- | --- | --- | --- |
| OpenCode 2.0.29 | `.agentic-blackbox/20261019-121927` | failed only `calculator_verified` (no public JS API, probe limitation). `model_applied_to_subagent` **true**, `telegram_fired` true | 2 / 10 / 0 | 4 / 12 |

- **Install:** `opencode-profile-defaults.json` is `{}`, and all `.opencode/opencode.json` agent models are `""`. The
  tier map is installed as `.agent/jev/opencode-model-tiers.json`.
- **Plugin context** (every spawn): `models` holds `openai/gpt-6.1-sol`, `openai/gpt-6-luna` and `openai/gpt-6-astra`,
  each with `prices: []`. `role_default` is `null`, with no pin.
- **Model requests:** 10 of 10 have `state.cost_source: tier_map` and 3 candidates (fast luna, balanced 6.1-sol,
  frontier astra; rank cost 1/2/3). `state.role_default.model` is non-null on all 10.

| Spawn | JEV answer | Outcome, reason | Tier / model_source / role_default_source | Model | Observed |
| --- | --- | --- | --- | --- | --- |
| explore (native) | fast 0.95 | jev_applied | fast / jev_tier / role_tier | openai/gpt-6-luna | openai/gpt-6-luna |
| analyst | balanced 0.36 | role_default_applied, `low_confidence` | fast / role_default / role_tier | openai/gpt-6-luna | openai/gpt-6-luna |
| team-lead | balanced 0.85 | role_default_applied, `low_confidence` | balanced / role_default / role_tier | openai/gpt-6.1-sol | openai/gpt-6.1-sol |
| developer | balanced 0.95 | jev_applied | balanced / jev_tier / role_tier | openai/gpt-6.1-sol | openai/gpt-6.1-sol |
| qa | balanced 0.56 | role_default_applied, `low_confidence` | balanced / role_default / role_tier | openai/gpt-6.1-sol | openai/gpt-6.1-sol |
| product-owner | balanced 0.32 | role_default_applied, `low_confidence` | balanced / role_default / role_tier | openai/gpt-6.1-sol | — (OpenCode: "Agent product-owner cannot run as a subagent") |
| instruction-reviewer | — (no JEV call) | rule_applied, `tier_fast_price_unknown` | — / review_model / — | openai/gpt-6-luna | openai/gpt-6-luna |
| memory-curator | fast 0.83 | role_default_applied, `low_confidence` | fast / role_default / role_tier | openai/gpt-6-luna | openai/gpt-6-luna |
| explore (after the follow-up) | fast 0.96 | jev_applied | fast / jev_tier / role_tier | openai/gpt-6-luna | openai/gpt-6-luna |
| developer (after the follow-up) | fast 0.45 | role_default_applied, `low_confidence` | balanced / role_default / role_tier | openai/gpt-6.1-sol | openai/gpt-6.1-sol |
| qa (after the follow-up) | fast 0.71 | role_default_applied, `low_confidence` | balanced / role_default / role_tier | openai/gpt-6.1-sol | openai/gpt-6.1-sol |

- **Spawn totals:** 3 `jev_tier`, 7 `role_default` and 1 review rule. No installed-role spawn ended with
  `model_source: none`. JEV never chose frontier.
- **Observations:** every one of the 10 matches its spawn's `result.model`.
- **Workflow:** `development-cycle-workflow` at 1.0, applied. The follow-up prompt got `clarify` 0.48 (native).
- **R1:** no 401/402/403/429 response and no `availability.json`. OAuth accepted the 6.1-sol overrides. Astra was never
  requested.
- **R3:** the native helper id is `explore` (`native_agent_type: explore`), and the map entry matched. `general` did not
  occur in this run.
- **AC-1:** 0 hits in the 12 `request.questions` and in the plugin's injected-context template.
- **Telegram (TG-HDR R5):**
  - 2 messages, both `✅ Задача завершена`, with the header `🤖 build · gpt-6-luna`.
  - Each comes from a completed native turn: the first turn delivered, and the harness follow-up turn delivered again.
  - No interim turn occurred.
