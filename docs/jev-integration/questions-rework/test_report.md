# JEV-QR — QA test report

Role: `qa`. Date: 2026-10-19. Branch `feature/JEV-questions-rework` (uncommitted tree). No production code was changed by QA.

## Summary

- Offline gates pass: `make lint`, `make test`, `make jev-rnd-verify`, size limits.
- AC-1 … AC-14 have real automated coverage. AC-13 offline part passes; the paid agreement measurement is **blocked** (no `JEV_API_KEY`).
- Blackbox: **Claude passed 10/10 checks**; OpenCode failed only `model_applied_to_subagent` (pre-existing, see QR-D2); Codex **blocked** by native hook trust.
- No blocking defect in the changed scope. 2 P2 and 1 P3 defects, all non-blocking; QR-D2 and QR-D3 are pre-existing.
- JEV ledger: `committed_usd` 1.94 → 2.12 (**+$0.18**, 105 calls total, +9). R&D spent $0.

## 1. Offline evidence (independent re-run)

| Command | Result |
| --- | --- |
| `make lint` | rc 0 |
| `make test` | rc 0. unit 158, integration 38, e2e 13 (Rust); content 20, jev hooks 75, notify 11 (Python); all OK |
| `make jev-rnd-verify` | rc 0 (core `summary.json`; questions results file absent, so it is skipped by design) |
| `wc -l extensions/codex/hooks/jev/*.py` | `questions.py` 383 (≤400), `hook.py` 445 (≤500), `routing.py` 186, `adapters.py` 185, `api.py` 299 |
| AC-11 size | `test_eighty_workflows_with_cyrillic_prompt_fit_the_request_limit` and `test_full_catalog_fits_the_jev_request_limit` pass; real OpenCode workflow request was 5 802 bytes |

## 2. Paid R&D (`JEV_RND_SUITE=questions`)

Command: `JEV_RND_SUITE=questions JEV_RND_BUDGET_USD=0.15 make -f docs/jev-rnd/Makefile live`.

Result: **blocked**, `RuntimeError: JEV_API_KEY missing`. `experiment.py` posts to the hosted endpoint
`https://jevtypesafeai.com/api/v1/decide` and reads only `JEV_API_KEY`. The repository `.env` holds only
`TYPESAFE_API_KEY` (a different provider; the runtime keeps the keys separate on purpose). QA did not send that key to
the other endpoint. No paid call, $0 spent, no `questions-results.json`.

Agreement per family (workflow_routing 12, model_tier 8): **not measured**. The threshold check (≥10/12, ≥6/8) is
open. Logged as QR-D1. Following the caller's instruction, the blackbox runs went ahead.

## 3. Blackbox runs

| Host | Run dir | Status |
| --- | --- | --- |
| Codex 0.163.0, `danger-full-access` | `.agentic-blackbox/20261019-003813` | **blocked**: "No Codex JEV hook event observed; review project hooks in /hooks". 0 JEV records, $0 |
| OpenCode 2.0.29, `openai/gpt-6-luna` | `.agentic-blackbox/20261019-003942` | failed 1 of 6 checks: `model_applied_to_subagent` |
| Claude Code 2.1.302, session `sonnet` | `.agentic-blackbox/20261019-004345` | **passed 10/10** |

Manual step for Codex (user only, QA did not bypass trust): in `/tmp/agentic-jev-blackbox-codex-cbdhtpj2` run
`codex`, open `/hooks`, trust the project hooks, then run
`BLACKBOX_CODEX_SANDBOX=danger-full-access BLACKBOX_ARGS="--run-dir .agentic-blackbox/20261019-003813" make blackbox-codex`.

### OpenCode (records in `/tmp/agentic-jev-blackbox-opencode-2ge4e_fg/.agentic/jev`)

- Questions asked: workflow 2, model 0, permission 0. Applied 1/2.
- Prompt 1 (`разработай калькулятор`): `development-cycle-workflow`, confidence 1.0, `jev_applied`. The agent read the workflow.
- Prompt 2 (the blackbox approval follow-up): `clarify` 0.47 → `low_confidence`, native.
- Spawns 10 (explore ×4, analyst, team-lead, developer, qa, instruction-reviewer, memory-curator): all
  `fallback/no_tier_routing`, `model_source: none`, outcome `native`. The plugin sent `models: []` and `role_default: null` (QR-D2).
- Observed models: `openai/gpt-6-luna` for all 7 observations; `explore` observation has `agent: null`, `native_agent_type: explore`.
- Probe verified `src/calculator.js:calculate`; Telegram fired.

### Claude (records in `/tmp/agentic-jev-blackbox-claude-tjte50gc/.agentic/jev`)

- Questions asked: workflow 1, model 3, permission 3. Applied **2/7** (baseline 2/11).
- `model-defaults.json` is v2 (`roles` + `tiers` haiku/sonnet/opus).

| Question | JEV answer | Threshold | Outcome | Tier / model_source | Applied model | Observed |
| --- | --- | --- | --- | --- | --- | --- |
| workflow | development-cycle-workflow 1.00 | 0.9 | jev_applied | — | — | workflow read |
| team-lead spawn | balanced 0.80 | 0.9 | role_default_applied (`low_confidence`) | frontier / role_default | opus | `claude-opus-5-5` |
| developer spawn | balanced 0.92 | 0.9 | jev_applied | balanced / jev_tier | sonnet | `claude-sonnet-5-5` |
| qa spawn | balanced 0.53 | 0.9 | role_default_applied (`low_confidence`) | balanced / role_default | sonnet | `claude-sonnet-5-5` |
| permission (qa, Bash `mkdir`…) | deny 0.20 | 0.9 | native (`low_confidence`) | — | — | — |
| permission (developer, Bash `sed`…) | deny 0.22 | 0.9 | native (`low_confidence`) | — | — | — |
| permission (developer, Bash `mkdir`…) | deny 0.28 | 0.9 | native (`low_confidence`) | — | — | — |

- The developer did **not** get opus. No spawn inherited the session model.
- Spawn state: no `default_model`; `cost_source: tier_order`, `quota: unknown`; the team-lead assignment was truncated at 2 500 characters with `assignment_truncated: true`.
- Permission state: `targets: []`, `command {program, length, args, shell_operators}`, `agent` is an installed role,
  `auto_allow_eligible: false`, no command text.
- Probe verified `src/calculator/evaluator.py:evaluate`; agents, commands, skills and rules loaded; Telegram fired.

### Runtime AC-1 check

Only `request.questions` (instructions and criteria) and the hook-injected context, rebuilt with
`adapters.workflow_context` and `adapters.model_reason`, were scanned. State was excluded (D2). Hits for
`calculator|crud`: **0** on OpenCode (2 requests sent; 1 injected workflow context), **0** on Claude (7 requests; workflow and 3 model contexts). No hook errors in the traces
(the "Traceback" matches were the agent's own test commands).

## 4. AC coverage matrix

| AC | Evidence | Result |
| --- | --- | --- |
| AC-1 | `test_runtime_sources_never_name_the_test_case` (4 runtime files), `test_requests_and_injected_context_never_name_the_test_case`, `test_selection_text_never_names_the_held_out_case`; runtime 0 hits | pass |
| AC-2 | `test_parse_workflow_requires_type_workflow`, `test_workflow_context_model_and_repeat_are_scoped` (GENERAL prefix, native/clarify), `test_eighty_workflows…`; runtime: 10 workflows + native + clarify, only `development-cycle-workflow` prefixed | pass |
| AC-3 | `test_native_and_clarify_answers_keep_native_behaviour_with_reason_codes`, `test_explicit_workflow_and_models_are_preserved`, Claude `test_explicit_workflow_adds_agent_tool_context` | pass |
| AC-4 | state key-set assert in `test_workflow_context_model_and_repeat_are_scoped`; `test_snapshot_reports_bounded_facts_without_following_symlinks`, `test_depth_limit_and_guidance_only_repository`; runtime state keys match | pass (entry bound tested with a small limit, not 5000) |
| AC-5 | `test_assignment_is_truncated_and_session_model_is_absent`, state asserts in `test_workflow_context…`; runtime Claude spawn state | pass |
| AC-6 | `test_confident_tiers_map_to_aliases`, `test_low_confidence_spawn_uses_profile_role_default`, `test_role_default_on_codex_and_opencode_fallbacks`, `test_clarify_and_api_error_route_to_role_default`; runtime Claude 1 jev_tier + 2 role_default | pass (Claude runtime); OpenCode runtime not reachable (QR-D2); Codex blocked |
| AC-7 | `tests/cli.rs` v2 asserts (Codex `:102-104`, Claude `:1218-1219`), `test_v2_and_legacy_defaults`, `test_legacy_flat_codex_defaults_still_give_role_default`, `test_opencode_tiers_from_one_to_four_priced_models`; runtime Claude v2 file | pass |
| AC-8 | `test_permission_state_is_metadata_only_and_keeps_decision_history`, `test_permission_limits_resist_even_confident_allow`, `test_targets_and_command_metadata`, `test_decision_history_is_capped`, Claude `test_permission_agent_label_only_for_installed_roles`; runtime 3 Claude permission states | pass |
| AC-9 | `test_configured_thresholds_and_invalid_values`, `test_threshold_range_and_default`, `manifest::reinstall_keeps_jev_tuning` | pass |
| AC-10 | record-field asserts in `test_role_default_on_codex_and_opencode_fallbacks` / `test_native_and_clarify…`, `test_multiple_subagents_keep_distinct_native_observations`; runtime all records carry the fields; `blackbox_jev.py verify` still works | pass |
| AC-11 | 80-workflow Cyrillic test, full-catalog test | pass |
| AC-12 | `tests/content/test_workflow_selection.py` (6 tests); 73/73 workflows have `selection`; template, GUIDE, CONTRIBUTING updated | pass |
| AC-13 | `tests/jev/test_rnd_fixtures.py` (6 tests), `make jev-rnd-verify` rc 0 | pass offline; **live agreement blocked** (QR-D1) |
| AC-14 | `make lint`, `make test` rc 0 | pass |
| AC-15 | OpenCode and Claude executed and recorded; Codex recorded as blocked with reason; +$0.18 ≤ $5 | pass (Codex blocked, allowed by AC text) |
| AC-16 | README, `example-request.json` (drift test `test_documented_example_matches_the_runtime_question`), guidance-update note, CONTRIBUTING, CHANGELOG mention the new behaviour | pass (inspection) |

## 5. Defect log

| ID | Severity | Summary | Business impact | Status |
| --- | --- | --- | --- | --- |
| QR-D1 | P2, environment, non-blocking | R&D live suite cannot run: `experiment.py` needs `JEV_API_KEY` for the hosted endpoint, and `.env` has only `TYPESAFE_API_KEY`. Repro: the command in §2. | No measured agreement for the new routing and tier rubrics. The design gate ("agreement before blackbox") stays unmet. | open; needs a key or an endpoint choice from the owner |
| QR-D2 | P2, pre-existing, non-blocking | OpenCode default install: the plugin builds the candidate pool only from agent model pins (`opencode.json` agents have `"model": ""`), and `opencode-profile-defaults.json` is `{}`. So `models: []`, `role_default: null`, and every spawn ends in `no_tier_routing` / `model_source: none`. No model question is sent. Repro: `make blackbox-opencode`, inspect spawn records. | OpenCode users get no tier routing and no role default; all subagents run on the session model. Same outcome as the 2026-10-16 baseline (`no_decision` on 10 spawns). | open; follow-up for developer |
| QR-D3 | P3, pre-existing | `api.redact` pattern `ts_[A-Za-z0-9_-]{8,}` has no word boundary. `tests_and_review_evidence` becomes `tes[REDACTED]` in records and review packets. `run_event` scrubs the incoming event, so `rename the parts_inventory_service module` reaches JEV as `rename the par[REDACTED] module`. | Corrupted evidence; a small loss of prompt accuracy for identifiers that contain `ts_`. | open; follow-up |

## 6. Residual risks

- Codex runtime behaviour (tiers luna / 6.1-sol / astra, role default, D6 `qa`) is not observed this cycle. Owner: user (hook trust) → QA rerun.
- Model and permission confidence stays low: Claude 1/3 model answers and 0/3 permission answers cleared 0.9. The improvement over the baseline is that fallbacks now go to the role default, not to the session model. Owner: team-lead (threshold tuning per type, AC-9 makes it configurable).
- A follow-up user message (OpenCode approval reply) triggers a new paid workflow question; it fell back here. A confident answer could re-route a running task. Owner: team-lead.
- The typesafe endpoint returned `usage.cost_usd: null`, so records report $0 and the ledger reserves a conservative amount per call. The real spend is likely lower than $0.18.
- Single run per host; LLM behaviour is non-deterministic.

## Iteration 2 (Scope change 1), 2026-10-19

### Summary

- Offline gates pass. Every iteration-2 test the coordinator listed exists. P2(c) has no direct test (see the coverage table).
- Paid R&D ran through `api.evaluate` against `https://api.typesafe.ai/v1/systemone`: **workflow_routing 12/12, model_tier 8/8** (24/24 and 16/16 calls, both option orders). QR-D1 closed.
- Claude: 28 ineligible permission events were recorded as `not_auto_allow_eligible` with no JEV call. The developer ran on sonnet (`jev_tier`, 0.97), not opus.
- Both blackbox reruns report `failed`. In neither case did routing fail:
  - Claude fails `model_applied_to_subagent` because of a label mismatch between spawn and observation records (**QR-D6, new, regression against AC-10**) and the follow-up task split (QR-D7).
  - OpenCode fails `model_applied_to_subagent` (QR-D2, deferred) and `calculator_verified` (the agent delivered a DOM-only IIFE with no public API, a probe limitation).
- Ledger `committed_usd`: 2.12 → 3.18 (**+$1.06**: R&D +0.80, OpenCode +0.04, Claude +0.22). Total 3.18 of 5; $1.82 headroom left for Codex.

### Offline evidence

| Command | Result |
| --- | --- |
| `make lint` | rc 0 |
| `make test` | rc 0. Rust 158 / 38 / 13; content 20, jev hooks 82, notify 11 |
| `make jev-rnd-verify` (before and after the paid run) | rc 0 |
| `wc -l` | `questions.py` 398, `hook.py` 489, `api.py` 312, `routing.py` 186, `adapters.py` 185 |

| Item | Test | Result |
| --- | --- | --- |
| not_auto_allow_eligible: no call | `test_permission_limits_resist_even_confident_allow` (`evaluate` would raise), `test_permission_state_is_metadata_only…` (skipped `&&` command) | covered |
| allow → ask still holds | `test_confident_allow_still_downgrades_when_eligibility_is_lost` (direct `map_permission`) | covered |
| P2(a) per-entry deadline | `repo_snapshot(project, seconds=-1)` in `test_questions.py` | covered |
| P2(b) outside / symlink / secret_like / temp | `test_outside_symlinks_and_secrets_are_never_inspected` | covered |
| P2(c) guarded `api` import | no test removes `api`; the tests patch `questions` / `adapters` to `None` instead | **gap** (code inspected: `read_json is None` → `load_runtime` returns `None`) |
| P2(d) adapters write identifier-only `runtime_incomplete` records | `test_partial_runtime_writes_identifier_only_records` | covered |
| P2(e) request kept on mapping failure | `test_request_is_kept_when_answer_mapping_fails` | covered |
| QR-D3 redaction, both directions | `Redaction.test_identifiers_with_key_prefixes_survive_and_tokens_do_not`; QA probe: `parts_inventory_service` and `tests_and_review_evidence` stay intact; `ts_live9aZk3QwErTy`, `sk-proj-…`, `jv_live_…` and `TYPESAFE_API_KEY=…` are redacted | covered; see QR-D8 |
| R&D client reuse | `test_official_endpoint_uses_the_typesafe_key_through_api_evaluate`, `test_missing_key_and_client_fallback_stop_before_or_at_the_call` | covered |

### Paid R&D

Command: `AGENTIC_JEV_BUDGET_FILE=.agentic-blackbox/jev-budget.json JEV_RND_SUITE=questions JEV_RND_BUDGET_USD=0.15 make -f docs/jev-rnd/Makefile live`. QA set the ledger variable so the spend counts toward the $5 cap.

- 40 calls, stop reason `completed`, model `jev-1.13.0`. `cost_reported: false` on every call.
- The suite's admission estimate was $0.092. The ledger booked $0.80 ($0.02 reservation per call with an unknown cost).
- Agreement: **12/12** workflow cases and **8/8** tier cases, in both option orders. There were no disagreements.
- These cases agreed with the expected label but scored below the 0.9 threshold, so at runtime they would fall back:

| Case | Expected | Got (normal / reversed) |
| --- | --- | --- |
| tier_pagination | balanced | balanced 0.91 / **0.75** |
| tier_architecture | frontier | frontier **0.79** / **0.80** |
| tier_small_program | fast or balanced | balanced 0.92 / **0.89** |
| tier_ru_sessions | frontier or balanced | frontier **0.53** / **0.53** |

All 24 workflow calls were at ≥ 0.91 (lowest: `wf_ru_vague` clarify, 0.91 reversed).

### Blackbox reruns

| Host | Run dir | Checks failed | Questions (wf / model / perm) | Applied |
| --- | --- | --- | --- | --- |
| Codex | — | not run; still **blocked** on hook trust (`.agentic-blackbox/20261019-003813`) | — | — |
| OpenCode 2.0.29 | `.agentic-blackbox/20261019-010215` | `model_applied_to_subagent` (QR-D2), `calculator_verified` (no public API) | 2 / 0 / 0 | 1 / 2 |
| Claude 2.1.302 | `.agentic-blackbox/20261019-010517` | `model_applied_to_subagent` (QR-D6, QR-D7) | 2 / 8 / 1 | 3 / 11 |

OpenCode details:
- Workflow `development-cycle-workflow` at 1.0, applied. The follow-up prompt got `development-cycle-workflow` at 0.50 (fallback).
- 12 spawns, all `no_tier_routing` / `model_source: none`. All 7 observations show `openai/gpt-6-luna`.

Claude details (one approval follow-up was sent):

| Spawn | JEV answer | Outcome | model_source | Model | Observed |
| --- | --- | --- | --- | --- | --- |
| Explore | fast 1.00 | jev_applied | jev_tier | haiku | `claude-haiku-5-5` |
| team-lead ×3 | balanced 0.67 / 0.51 / 0.73 | role_default_applied | role_default | opus | `claude-opus-5-5` |
| developer | balanced 0.97 | jev_applied | jev_tier | sonnet | `claude-sonnet-5-5` |
| qa ×2 | balanced 0.33 / 0.47 | role_default_applied | role_default | sonnet | `claude-sonnet-5-5` |
| instruction-reviewer | — (`configured_lightweight_price_unknown`) | rule_applied | review_model | haiku | `claude-haiku-5-5` |
| memory-curator | fast 0.63 | role_default_applied | role_default | haiku | `claude-haiku-5-5` |

Other Claude findings:
- Workflow at 1.0, applied. The follow-up prompt got `clarify` at 0.51 (fallback).
- Permissions, 29 events:
  - 28 were Bash with `auto_allow_eligible: false` → `fallback/not_auto_allow_eligible`, `outcome: native`, `request: null`. No JEV call was made, from Explore, product-owner, team-lead, developer or qa.
  - 1 eligible `Write` (qa) was asked: allow 0.69 → `low_confidence`, native.
- The developer was **not** on opus.
- Runtime AC-1 check: 0 hits on either host.

### AC matrix (iteration 2)

| AC | Result | Note |
| --- | --- | --- |
| AC-1 | pass | unit tests and runtime, 0 hits |
| AC-2, AC-3, AC-4, AC-5, AC-7, AC-9, AC-11, AC-12, AC-14, AC-16 | pass | re-run green; no change in behaviour |
| AC-6 | pass | Claude runtime: 2 `jev_tier`, 6 `role_default`; OpenCode not reachable (QR-D2, deferred); Codex blocked |
| AC-8 (amended) | pass | unit tests and 28 runtime records with no JEV call |
| AC-10 | **fail (compatibility clause)** | fields are present, but `blackbox_jev.py verify` can no longer match native-helper spawns to their observations (QR-D6) |
| AC-13 | pass | live agreement 12/12 and 8/8; `jev-rnd-verify` rc 0 |
| AC-15 | pass with gaps | OpenCode and Claude re-recorded; Codex blocked (allowed); total spend $3.18 ≤ $5 |

### Defects (iteration 2)

| ID | Severity | Summary | Business impact | Status |
| --- | --- | --- | --- | --- |
| QR-D1 | — | R&D key and endpoint | — | **closed** |
| QR-D3 | — | over-eager redaction | — | **closed** (verified both directions) |
| QR-D4 | — | ineligible permission calls | — | **closed** (28 records, no call) |
| QR-D6 | P2, new regression, non-blocking for end users | The spawn record keeps a native helper label (`context.agent: "Explore"`), but the observation record for the same subagent is normalised to `agent: null`, `native_agent_type: "Explore"`. `blackbox_jev.py verify` matches `a.context.agent == b.context.agent`, so JEV-applied helper routing (Explore haiku 1.0 → `claude-haiku-5-5`) is not credited. Repro: `BLACKBOX_ARGS="--verify-only --run-dir .agentic-blackbox/20261019-010517" make blackbox-claude`, then compare spawn and observation `context`. | The release evidence cannot prove model routing on runs where only helper spawns are in the first task. Breaks AC-10's "blackbox script compatibility". Routing itself works. | open; needs a fix in the developer's scope (normalise spawn labels the same way, or match on `native_agent_type`) |
| QR-D7 | P3, harness, pre-existing | The approval follow-up creates a new `task_id`. `verify` counts only the records of the first prompt's task, so spawns after the follow-up (the developer `jev_tier` sonnet) are ignored. | False `failed` in blackbox results when the coordinator stops for approval. | open; follow-up (harness) |
| QR-D8 | P3, new side effect of the QR-D3 fix | `api.TOKEN` now needs a digit in the body, so a digit-free token such as `sk-abcdefghijklmnopqrstuv` is no longer redacted. Configured keys are still scrubbed exactly by `scrub`. | Low: real provider keys contain digits; it only matters for unknown keys pasted into prompts. | open; accept or tighten |
| QR-D2 | P2, deferred by PO | OpenCode: no role models, so no model routing | as before | deferred (team-lead) |

### Residual risks (iteration 2)

- Model confidence at runtime is still low for team-lead and qa (0.33–0.73). Role defaults absorb it safely, but JEV routing applies to only 2 of 8 model questions.
- The ledger books $0.02 per call when the cost is unknown. R&D's own $0.15 cap used the estimate ($0.09), while the ledger booked $0.80. Headroom is $1.82 for the Codex run.
- Codex is not verified in this iteration.

## Iteration 3 (offline only), 2026-10-19

No paid calls. Ledger `committed_usd` stays 3.18 before and after (158 calls).

### Offline evidence

| Command | Result |
| --- | --- |
| `make lint` | rc 0 |
| `make test` | rc 0. Rust 158 / 38 / 13; content 20, jev hooks 86, notify 11 |
| `make jev-rnd-verify` | rc 0 (`summary.json` now has a `questions` section) |
| `wc -l` | `questions.py` 398, `hook.py` 490, `api.py` 319, `routing.py` 186, `adapters.py` 185 |

| Item | Test | QA probe |
| --- | --- | --- |
| QR-D6 labelling | `test_claude_hooks.py::test_spawn_and_observation_label_agents_the_same_way` | — |
| QR-D6 verify pairing | `test_blackbox.py::test_native_helpers_are_matched_by_native_agent_type` (native, legacy record, mismatch) | `--verify-only` on recorded Claude run, below |
| Redaction kept intact | `Redaction.test_identifiers_with_key_prefixes_survive` | `tests_and_review_evidence`, `parts_inventory_service`, `task-ask-me`, `ts_inventory_service`, `risk-sk-assessment` unchanged |
| Redaction applied | `Redaction.test_provider_tokens_are_redacted` | `sk-proj-` and `sk-` letters-only (20+), `sk-ant-`, `ghp_`, `AKIA…`, `xoxb-`, `ts_live9…`, `jv_live_…` all redacted. QR-D8 closed |
| P2(c) | `test_hooks.py::test_missing_api_module_falls_back_with_runtime_incomplete` (subprocess, copied runtime without `api.py`) | gap closed |

### Re-verification of the recorded runs (`--verify-only`, no model requests)

| Host | Run | Status | `model_applied_to_subagent` |
| --- | --- | --- | --- |
| Claude | `.agentic-blackbox/20261019-010517` | **passed 10/10** | true. Pairs the Explore spawn (haiku, `jev_tier` 1.0) with `claude-haiku-5-5`, using the legacy-record path |
| OpenCode | `.agentic-blackbox/20261019-010215` | failed (unchanged) | false (QR-D2, deferred). `calculator_verified` false: no public API (probe limitation) |

QR-D7 still limits the evidence. On Claude, only the Explore spawn sits in the first task. The developer `jev_tier` sonnet
spawn (observed `claude-sonnet-5-5`) comes after the approval follow-up and is still not counted. `--verify-only`
rewrote `results.json` in both run dirs with the new verdicts.

### Final AC matrix

| AC | Result | Evidence |
| --- | --- | --- |
| AC-1 | pass | unit tests and runtime scan, 0 hits (OpenCode and Claude, two iterations) |
| AC-2 | pass | unit tests; runtime: 10 workflows + `native` + `clarify`, one `GENERAL.` |
| AC-3 | pass | unit tests |
| AC-4 | pass | unit tests (per-entry deadline and cap); runtime state keys |
| AC-5 | pass | unit tests; runtime Claude spawn state |
| AC-6 | pass | Claude runtime `jev_tier` + `role_default`; OpenCode path not reachable (QR-D2, deferred); Codex blocked |
| AC-7 | pass | Rust and Python tests; runtime v2 `model-defaults.json` |
| AC-8 (amended) | pass | unit tests; 28 runtime `not_auto_allow_eligible` records with no JEV call |
| AC-9 | pass | unit tests and `reinstall_keeps_jev_tuning` |
| AC-10 | **pass** | QR-D6 fixed; labelling and pairing tests; Claude `--verify-only` passes |
| AC-11 | pass | 80-workflow Cyrillic and full-catalog tests |
| AC-12 | pass | content tests; 73/73 workflows |
| AC-13 | pass | live agreement 12/12 and 8/8; `jev-rnd-verify` rc 0 |
| AC-14 | pass | `make lint`, `make test` rc 0 |
| AC-15 | pass (Codex blocked, allowed) | OpenCode and Claude recorded; total $3.18 ≤ $5 |
| AC-16 | pass | docs, CHANGELOG, R&D README (ledger note) |

### Defect status (final)

| ID | Severity | Status |
| --- | --- | --- |
| QR-D1, QR-D3, QR-D4, QR-D6, QR-D8 | — | closed |
| QR-D2 | P2, pre-existing | deferred by PO (team-lead) |
| QR-D7 | P3, harness, pre-existing | open follow-up; it under-counts evidence, it does not hide failures |
| D6 (Codex `qa` default not a candidate) | P1 follow-up | deferred by PO |

No open blocking defect.

### Residual risks

- Codex runtime is not verified. Pending user hook trust; $1.82 ledger headroom left.
- Runtime model confidence is low for team-lead and qa. Role defaults absorb it; JEV applied only 2 of 8 Claude model questions.
- Single runs per host; LLM output varies (for example, an OpenCode calculator without a public API).

## Iteration 3: Codex run and OpenCode model-routing check, 2026-10-19

### Summary

- Codex ran after the user trusted the hooks. **AC-15 on Codex: GO.** The run was executed and recorded in full. The
  blackbox status `failed` comes from two checks, and neither is an AC-15 criterion:
  - `model_applied_to_subagent`: no confident tier was given; role-default fallbacks are not counted, by design.
  - `telegram_fired`: a harness path defect (QR-D9).
- The OpenCode model question is still **not exercised at runtime**. With the OpenAI profile, OpenCode exposes
  `cost: []` (oauth). The profile model ids also leave only one eligible model. See QR-D10 and QR-D11.
- Ledger `committed_usd` 3.18 → 3.32 (**+$0.14**, 158 → 165 calls). Codex +$0.10 (5 calls), OpenCode +$0.04 (2 calls).
  Total $3.32 of $5.
- QA changed no product, harness or test code.

### Codex (`.agentic-blackbox/20261019-003813`, records in `/tmp/agentic-jev-blackbox-codex-cbdhtpj2/.agentic/jev`)

Pre-run check: the installed `api.py`, `hook.py` and `questions.py` were stale (pre-iteration-2 hashes). `adapters.py`
and `routing.py` were current. Codex stores trust per `hooks.json` entry hash (`[hooks.state."…/hooks.json:<event>:i:j"]
trusted_hash`), not per script content. A scratch install with the current binary gave a byte-identical `hooks.json`.
The documented `--run-dir` command reinstalls anyway, and trust held: `hooks.json` sha256 `c139a43f…` was unchanged
before and after, and 102 records were written. After the run, all five files equal the source plus the generated
header. Note: Codex trust does not cover the hook script bodies.

Command: `BLACKBOX_CODEX_SANDBOX=danger-full-access BLACKBOX_ARGS="--run-dir .agentic-blackbox/20261019-003813" make blackbox-codex`
(log `.agentic-blackbox/codex-run4.log`).

| Check | Result |
| --- | --- |
| native_exit_success, real_jev_workflow, workflow_read_by_agent, calculator_verified | true |
| model_applied_to_subagent | false (0 `evaluated` spawns) |
| telegram_fired | false (QR-D9) |

- Questions: workflow 1, model 4, permission 0 (`danger-full-access` raises no permission requests). Applied 1/5.
- Workflow: `development-cycle-workflow` at 0.99 → `jev_applied`.
- Model: all 4 answers were `clarify`, with confidence 0.40 / 0.47 / 0.52 / 0.60 and `balanced` at 0.26–0.41. State had
  `assignment_unavailable: true` (host-encrypted assignment).
- Spawn results:
  - product-owner, team-lead and developer → `role_default_applied`, tier `balanced`, `model_source: role_default`,
    `gpt-6.1-sol`. Observed `gpt-6.1-sol` for each.
  - qa → `native`, `model_source: none`, `role_default: null` (D6). Observed `gpt-6-astra` (session model, frontier).
- Tier mapping: candidates were `fast gpt-6-luna`, `balanced gpt-6.1-sol` and `frontier gpt-6-astra`, with
  `cost_source: tier_order`. This matches `extensions/codex/model-tiers.json`. The installed `model-defaults.json` is v2.
- AC-1: 0 hits in `request.questions` (5 requests) and in the rebuilt injected context (1 workflow, 3 model reasons).

### OpenCode model routing (Task 2)

**(a) Payload and prices.**

| Run | `models` sent | `prices` | `role_default` | Spawn outcome |
| --- | --- | --- | --- | --- |
| `20261019-010215` (default install) | `[]` | — | `null` | 12 × `fallback/no_tier_routing`, `model_source: none` |
| `20261019-114054` (`AGENTIC_OPENCODE_PROFILE=openai`) | `[{id: "openai/gpt-6-luna", …}]` | `[]` | profile value (`openai/gpt-6-luna`, bare `gpt-6.1-sol`, or `openai/gpt-6-terra`) | 17 × `routed/single_eligible_model` → `openai/gpt-6-luna` |

- `opencode models` lists these OpenAI ids: `gpt-6-astra(-fast, -ultrafast)`, `gpt-6-luna(-fast)`, `gpt-6-sol(-fast)`
  and `gpt-6.1-sol(-fast, -ultrafast)`. There is no `gpt-6-terra`.
- Cost shape:
  - The models.dev cache `~/.cache/opencode/models.json` has dicts: luna `{input 0.1, output 0.5, …}`, 6.1-sol
    `{2, 10}`, astra `{10, 50}`. 49 of 53 OpenAI models have a dict; 4 image models have none.
  - SDK v2 types (`@opencode-ai/sdk` 1.15.7, `dist/v2/gen/types.gen.d.ts`): `ModelV2Info.cost` is
    `Array<{tier?, input, output, cache}>`.
  - At runtime, the plugin received `cost: []`. OpenCode authenticates `openai` by `oauth`; trace steps show `"cost": 0`.
- The hook does not rewrite `prices`. `routing.price([])` is `None`, and `opencode_tiers` with unpriced models is `{}`.
- Offline probe of `routing.opencode_tiers` with the catalog prices: list shape and dict shape both give fast luna,
  balanced 6.1-sol and frontier astra.

**(b) Run with role models.** Run `20261019-114054` was prepared and executed with `AGENTIC_OPENCODE_PROFILE=openai`, an
installer option, with no product change. QA started it after reading the models.dev cache prices and before seeing the
runtime `cost: []`. The coordinator's skip condition (no prices) turned out to hold at runtime, and the run cost $0.04.

- What it shows:
  - only one model was eligible, so no model question was sent;
  - no tiers were derived;
  - no `role_default` fallback path ran;
  - the observed model was `openai/gpt-6-luna` (10 of 10).
- Workflow: 1.0 → applied. The follow-up prompt got 0.49 → native. Telegram fired; with the absolute `--run-dir` the
  credentials resolved.
- `calculator_verified` false: no public Python/JS API (probe limitation).

**What a fix needs** (input for the QR-D2 design; QA did not implement it):

1. A price source that works under oauth. Options:
   - read models.dev `cost` (or a shipped static table);
   - use a deterministic host tier map, like Codex `model-tiers.json`, when the runtime prices are empty.

   This is a product change (plugin or hook), because AC-7 now says "unknown prices → no tier routing".
2. Fix the OpenAI OpenCode profile model ids: add the `openai/` prefix to `gpt-6.1-sol`, and replace `gpt-6-terra`. This
   is a product content change.
3. A harness-only change cannot help: a profile with valid ids still yields `prices: []`.

### Defects (iteration 3)

| ID | Severity | Summary | Evidence | Status |
| --- | --- | --- | --- | --- |
| QR-D9 | P3, harness | A relative `--run-dir` makes `AGENTIC_CONFIG_DIR` relative (`scripts/blackbox_jev.py:265`). The Codex Stop hook runs in the project cwd, so the fake credentials are not found and `telegram_fired` is a false negative. Workaround: pass an absolute `--run-dir`. | `/tmp/agentic-jev-blackbox-codex-cbdhtpj2/.agentic/telegram-debug.log`, `.agentic-blackbox/20261019-003813/codex/telegram.json` (0 requests) | open |
| QR-D10 | P2, design gap, blocks the QR-D2 fix | OpenCode with OpenAI oauth gives `cost: []` from `ctx.model.list()`. Under AC-7 no tier routing is possible, even with ≥2 role models. Impact: OpenCode users never get JEV tier routing on the subscription setup. | `/tmp/agentic-jev-blackbox-opencode-k_jrpiq6/.agentic/jev/event-*.json` (`context.models[].prices: []`), `.agentic-blackbox/20261019-114054/opencode/trace.jsonl` (`"cost": 0`) | open; input to the QR-D2 design (team-lead) |
| QR-D11 | P2, content | `extensions/opencode/profiles/openai/opencode.json` uses the bare `gpt-6.1-sol` (product-owner, team-lead, devops-engineer, plan, build) and `openai/gpt-6-terra` (developer, not in the catalog). The plugin pool keys on `provider/id`, so only luna is eligible, and the developer `role_default` names a model that does not exist. | spawn `context.role_default` in the run above; `opencode models` output | open |
| QR-D12 | P2, behaviour | Codex model questions are effectively unanswerable: the assignment is host-encrypted (`assignment_unavailable: true`), and JEV answered `clarify` 4/4 (0.40–0.60). Codex model routing runs on role defaults only. | Codex spawn records, `result.answers.model` | open; team-lead (state or rubric) |
| D6 | P1 follow-up, deferred | Observed: qa `role_default: null` (`gpt-6-terra` not a candidate) → qa ran on the session `gpt-6-astra` (frontier). | Codex qa spawn and observation records | deferred by PO |

### AC impact

- AC-6: pass on Codex for the role-default path (3 spawns, observed models match). The confident `jev_tier` path is not
  observed on Codex (QR-D12). OpenCode is still not reachable.
- AC-7: the OpenCode clause behaves as specified ("unknown prices → no tier routing"). On real OpenAI oauth this means
  the OpenCode tier routing never activates (QR-D10).
- AC-15: **pass on all three hosts**. Codex is now executed and recorded. Total spend $3.32 ≤ $5.

## Iteration 4/4a: QR-D2 fix verification, 2026-10-19

### Summary

- **Recommendation: GO** for AC-17 to AC-20 and for AC-6 as amended. No blocking defect.
- Offline gates are green. 82 independent QA probe checks pass. The paid OpenCode run exercised real model routing
  for the first time: 10 model questions, 3 `jev_tier`, 7 `role_default`, and observed models equal the applied
  models.
- Ledger `committed_usd`: 3.32 → 3.56 (**+$0.24**, 12 calls). The ceiling was $3.92. There was no re-run and no Codex
  re-run. The total is $3.56 of $5.
- QA changed no product, harness or test code.

### Offline evidence

| Command / check | Result |
| --- | --- |
| `make lint` | rc 0 |
| `make test` | rc 0. Rust 161 / 38 / 13; content 25, jev hooks 105, notify 31 |
| `make jev-rnd-verify` | rc 0 |
| `wc -l` | `hook.py` 484, `questions.py` 398, `routing.py` 270, `agentic-jev.ts` 174, `jev_hooks.rs` 465, `jev_defaults.rs` 185: all within limits |
| `ast` scan, >30 lines | `routing.py` none. `hook.py` only `permission_boundaries` (45, pre-existing and unchanged, non-goal) |

**Independent probes** (`scratchpad/probe_iter4.py`): fresh default installs from the current binary. The script calls
`hook.run_event` / `adapters.codex_event`, with `hook.evaluate` replaced so that no JEV call is made.

| Area | Checks | Result |
| --- | --- | --- |
| AC-17 | 8 installed roles + native `explore` and `general` × {`clarify` 0.5, `balanced` 0.89, API error}. Each case expects: `state.cost_source tier_map`, ≥2 candidates, `state.role_default.model`, and `result.model` (luna for fast roles, 6.1-sol for balanced), `model_source: role_default`, `role_default_source: role_tier`. Also: instruction-reviewer → luna `tier_fast_price_unknown` with no JEV call; confident frontier 0.95 → astra `jev_tier`; installed tier file is the v1 map and `opencode-profile-defaults.json == {}` | 34/34 pass |
| AC-18 | price shapes `[]`, partial, equal, all-zero, negative and bool → `tier_map`; distinct dict and SDK-v2 list bands → `catalog_price`; astra missing → fast+balanced; luna missing → balanced+frontier | 10/10 pass |
| P2-1 | copilot role default + OpenAI map models → `no_tier_routing`, copilot default kept; env provider with no map entry → no tiers (no file-order fallback); env `openai` wins over the role-default prefix; stale `openai/gpt-6-terra` profile default → `role_tier` 6.1-sol | 4/4 pass |
| Pins (I5) | `pinned_model`, `continuation`, pin + profile default → `preserved` / `pinned`, no model override, no JEV call; `configuration_unavailable` → keep native | 4/4 pass |
| Malformed tier map | 19 file contents (invalid JSON, empty, null, list, string, version `"1"`/`true`/`2`/`1.0`, list or string providers, non-string tier values, list roles, unknown or dict role tier, unknown tier key, 2000-level nesting, binary, 200 000 roles); the path as a directory, unreadable (mode 000), or a symlink loop; a missing file → no exception, today's behaviour | 23/23 pass |
| AC-6 amended | Codex qa, developer and analyst with an encrypted assignment → no JEV call, `assignment_unavailable`, role default (6.1-sol / 6.1-sol / luna); a plain Codex assignment still asks; an OpenCode spawn with `assignment_unavailable` still asks | 5/5 pass |
| D6 / install | Codex `roles.qa == gpt-6.1-sol`. Installed Codex TOMLs carry no `model` pin, so qa is routed, not pinned. (Checked separately: no `.opencode/model-tiers.json` in the scratch install.) | 2/2 pass |

Notes:
- Malformed-map behaviour is safe in every case. A map whose `roles` are invalid but whose `providers` are valid still
  routes confident tiers. Its role default is then `null`, so a fallback runs native.
- The `version: 1.0` float is rejected (strict `int`). This is conservative and acceptable.

**AC-20 against live catalogs** (not the frozen test snapshot):
- `opencode models | grep '^openai/'` lists 19 ids, including luna, 6.1-sol and astra.
- Every `openai` profile `model`, `fallback[]` and `small_model` is in that list with the `openai/` prefix
  (`openai/gpt-6-luna`, `openai/gpt-6.1-sol`, `openai/gpt-6-astra`). So is every tier-map value.
- Codex `models_cache.json` (`fetched_at` 2026-10-19T08:16Z, `visibility: list`) contains every source
  `extensions/codex/agents/*.toml` model. Each of those models is a `model-tiers.json` value.
- `gpt-6-terra` appears only in `profiles/githubcopilot/opencode.json` (PO exception, F1).

### Pre-flight (§5)

- The `openai/` catalog check passes.
- Ledger: 3.32, 165 calls, `pending: {}`.
- There was no `.active-run` lock and no harness process.

### Paid run (AC-19)

`env -u AGENTIC_OPENCODE_PROFILE make blackbox-opencode` → `.agentic-blackbox/20261019-121927`. The records are in
`/tmp/agentic-jev-blackbox-opencode-d9e7dr5d/.agentic/jev`, and the log in `.agentic-blackbox/opencode-run4.log`.
One approval follow-up was sent.

| Check | Result |
| --- | --- |
| native_exit_success, real_jev_workflow, workflow_read_by_agent | true |
| model_applied_to_subagent | **true** (first time on OpenCode) |
| telegram_fired | true |
| calculator_verified | false: a DOM app with no public JS API (probe limitation, as in earlier runs) |

**§5 evidence:**

| Expected | Observed |
| --- | --- |
| Profile defaults `{}` | `{}`; agent models `""` |
| Plugin context: ≥2 openai ids, `prices: []`, `role_default: null` | 3 ids (6.1-sol, luna, astra), all `prices: []`, `role_default: null` on all 11 spawns |
| ≥1 model request with `tier_map`, ≥2 candidates, non-null `state.role_default.model` | 10/10 |
| Per spawn, paired with the observation | see the `verification.md` iteration-4 table: 10 of 10 observations equal `result.model` |
| ≥1 `jev_tier` or `role_default` | 3 `jev_tier` (explore 0.95 / 0.96, developer 0.95) and 7 `role_default` |
| No installed-role spawn with `model_source: none` unless pinned | 0 |
| AC-1 | 0 hits (12 requests, plugin injected-context template) |
| R1, 4xx or cooldown on 6.1-sol / astra | none. 6.1-sol was accepted 5 times; astra was never chosen |
| R3, agent ids | native `explore` matches; `general` not seen in this run |

- **Confidence:** 3 of 10 model answers cleared 0.9. JEV picked a tier different from the role default in 2 cases
  (the second developer `fast` 0.45 and the second qa `fast` 0.71); both fell back.
- **Product-owner spawn:** the coordinator stayed on `build` and tried to spawn `product-owner`. OpenCode rejected it
  ("Agent product-owner cannot run as a subagent": product-owner is `mode: primary`). The hook had already spent one
  JEV call (QR-D13).

### TG-HDR R5 (live)

- `telegram.json` holds 2 `sendMessage` calls. Each starts with `✅ <b>Задача завершена</b> — … · OpenCode` and has the
  line `🤖 build · gpt-6-luna`.
- Each message belongs to a completed native turn, and each body reports delivery. In this harness, the follow-up runs
  whenever the probe cannot verify the calculator, so 2 `✅` for 2 final turns follows TG-3.
- No interim turn happened, so the live `💬` path was not observed. It is covered offline by T6.
- `telegram_fired` is reliable. With an absolute root the credentials resolve, and `RunRoot` covers relative
  `--run-dir`. The live relative-`--run-dir` path was not re-run.

### AC matrix (iteration 4)

| AC | Result | Evidence |
| --- | --- | --- |
| AC-6 (amended) | pass | QA probes (Codex skip, Codex-only); `test_codex_encrypted_assignment_skips_jev_and_applies_role_default`; runtime OpenCode `role_default` 7× |
| AC-17 | pass | probes 34/34; runtime: 10/10 non-null `state.role_default.model`, 3 candidates, raw `role_default: null` |
| AC-18 | pass | probes 10/10; unit tests; runtime `tier_map` with `prices: []` on all 11 spawns |
| AC-19 | pass | run `20261019-121927`; `model_applied_to_subagent` true |
| AC-20 | pass | live catalog checks; `tests/content/test_model_ids.py` |

### Defects (iteration 4)

| ID | Severity | Summary | Evidence | Status |
| --- | --- | --- | --- | --- |
| QR-D13 | P3 | The hook routes and asks JEV for a spawn of a `mode: primary` agent (`product-owner`), which OpenCode then rejects natively. Cost: one JEV call ($0.02 ledger) per occurrence; there is no user impact. Related observation: the root session stayed on `build` (Telegram header `🤖 build`), although the workflow initiator is product-owner. | tool record `subagent` `product-owner` `status: error`; trace `"Agent product-owner cannot run as a subagent"` | open, follow-up (skip primary-mode agents in the plugin or hook) |
| QR-D2, QR-D10, QR-D11, D6, QR-D12, QR-D9 | — | — | this section | **closed** (QR-D9 by unit test and absolute-root run) |
| QR-D7 | P3 | the follow-up turn opens a new task | — | open (F3) |

### Residual risks

- Single paid run. JEV model confidence is still modest (3 of 10 ≥ 0.9). The role defaults absorb the rest.
- Frontier (astra) was never requested at runtime, so its OAuth acceptance is unverified (R1, P3-2).
- `general` was not observed (R3, partial).
- The Codex QR-D12 skip is verified offline only. An optional Codex re-run was allowed (ledger 3.56 ≤ 3.72) and was
  skipped for budget prudence.
- The live interim (`💬`) Telegram path was not observed on OpenCode.
