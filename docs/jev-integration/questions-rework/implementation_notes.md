# JEV-QR — Implementation notes (developer)

Branch `feature/JEV-questions-rework`, version 1.4.0 (unreleased). Nothing is committed. No paid target was run.
Scope: notes.md §4 increments 1–3. Paid R&D and blackbox runs (AC-15, `verification.md`) are still open for QA.

## Increment 1 — Python runtime

- New `questions.py` (`VERSION = 2`): frontmatter parser, `parse_workflow` (`type: workflow` only), `workflow_criterion`
  with levels 0–3, `fit_criteria` (+ `native`, `clarify`), bounded `repo_snapshot`, `installed_areas`,
  `installed_roles`, builders `workflow_request` / `model_request` / `permission_request`, permission metadata
  (`path_kind`, `permission_target`, `command_meta`, `remember_decision`) and `threshold`. Instruction texts follow the
  approved plan; the tier rubric is adapted from `example-request.json` without test-case wording.
- `hook.py`: `run_event` is split into `open_turn`, `record_once`, `decide`, `handle_prompt`, `handle_spawn`,
  `handle_permission`, `apply_answer`, `map_*` and `finish_record`. A guarded `load_runtime()` falls back with
  `runtime_incomplete`. Identity has `'v': 2`. Requests are sent and size-checked with `ensure_ascii=False`. Record
  fields (D4) are top-level. Role default applies on every host (`model_source: role_default`); `default_model`,
  `claude_session_model` and the "calculator/CRUD" strings are gone. Agent labels are kept only for installed roles
  (permission and observation), otherwise `agent: null` + `native_agent_type`. `permission_boundaries` and
  `bounded_path` are byte-identical (md5 `5b41b35d…` before and after).
- Tests: new `tests/jev/test_questions.py`; `test_hooks.py` and `test_claude_hooks.py` updated (fixtures with
  `type: workflow`, tier answers, `role_default`, new cases for native/clarify, codex/opencode role default,
  thresholds, legacy defaults, tier overrides, identity v2, `runtime_incomplete`, permission metadata, AC-1 runtime
  check, Claude tier→alias and agent labels).

## Increment 2 — Installer and plugin

- `src/jev_hooks.rs`: assets and `source` arms for `questions.py`, `routing.py`, `adapters.py`; defaults come from
  `jev_defaults::model_defaults`.
- New `src/jev_defaults.rs`: v2 `{"version": 2, "roles", "tiers"}` (Claude-only → profile; any Codex → Codex, D7) and
  `manifest_settings`, which keeps `thresholds`, `lightweight_model`, `tiers` from the old manifest.
- `extensions/codex/model-tiers.json` (luna / 6.1-sol / astra); `copydir.rs` skips it so it is not copied to `.codex/`.
- `profile.json` `tiers` + `claude::profile_tiers` (shared `profile_section`).
- `manifest.rs`: `settings.jev` from `manifest_settings` + test `reinstall_keeps_jev_tuning`.
- `tests/cli.rs`: `["roles"]` / `["tiers"]` asserts, runtime files installed, no `.codex/model-tiers.json`.
- `agentic-jev.ts`: spawn sends `role_default` (agent model ?? profile default) and no `default_model`; permission
  sends `agent` from the session.
- `scripts/lint_review_pipeline.py`: the legacy-role-name allowlist moves from `hook.py` to `routing.py`, which now
  holds the alias table.

## Increment 3 — Content, R&D, docs

- A `selection` block after `agent:` in all 73 `areas/**/workflows/*.md`. Each has a specific `use-when`, and
  `avoid-when` where a nearby workflow could take the request (project setup, backend develop-feature, full-cycle,
  code review, CI onboarding). `general: true` is set only for `software/general/development-cycle-workflow`.
- `areas/template/workflow.tmpl.md` (block + instruction 5), `areas/template/GUIDE.md`, CONTRIBUTING "Adding a new
  workflow".
- `scripts/lint_prompts.py::check_workflows` uses the `questions.py` parser: `type: workflow`, map shape, boolean
  `general`, quoted non-empty `use-when` / `avoid-when` ≤ 300, no unknown keys, ≤ 1 general per top-level area.
  Tests: `tests/content/test_workflow_selection.py` (it also shows the real 73-workflow catalog fits in 32 KiB).
- R&D: `docs/jev-rnd/question_fixtures.py` builds `workflow_routing` (12, RU/EN, held-out) and `model_tier` (8) with
  the runtime builders. `experiment.py` supports `JEV_RND_SUITE=questions` → `questions-results.json`. `analyze.py`
  accepts list expectations and validates the questions file only when it exists. `summary.json` is unchanged
  without it. Tests: `tests/jev/test_rnd_fixtures.py`.
- Docs: `docs/jev-integration/README.md` (runtime modules, new section "Questions, tiers and records"), root
  `README.md` JEV summary, `example-request.json` regenerated from `model_request` (with a drift test),
  `docs/guidance-updates/2026-10-19-jev-questions-rework.md`, `docs/jev-rnd/README.md`, `CHANGELOG.md` v1.4.0. I
  also removed the now-false sentence "session model is read from the transcript".

## Deviations

1. **Two more runtime modules (`routing.py`, `adapters.py`) and client code in `api.py`.** After the planned split,
   `hook.py` was 825 lines and `questions.py` was 446, above the 500/400 gates. Compression could not close that gap
   without hurting readability. Fix: tier/price/spawn rules moved to `routing.py`; the Codex/Claude adapters moved to
   `adapters.py` (D3's P2 follow-up, done now); `read_json`, `save_json`, `scrub`, the budget ledger and `evaluate`
   moved to `api.py`, the existing JEV client that `hook.py` already imports without a guard. `hook.codex_event` /
   `hook.claude_event` are thin wrappers that pass the hook module, so `patch.object(hook, ...)` still works. The
   guard requires all three new modules at version 2.
2. **`load_defaults(data)` takes parsed JSON, not `project`**, and lives in `routing.py`. File I/O stays in `hook.py`.
3. **`model_request(..., cost_source='tier_order')`** takes a 5th keyword argument because state needs `cost_source`.
4. **The workflow question is asked with ≥ 1 workflow** (was > 1), because `native` and `clarify` always exist.
5. **The snapshot skips every hidden directory** and `vendor` / `dist` / `build` / `__pycache__`, not only the listed
   ones. Otherwise `.agent/jev/*.py` would count as project source in an empty repository.
6. **`applied` semantics:** `true` when a confident JEV choice decided the outcome, including workflow
   `native`/`clarify` and permission `ask`. Model `clarify` (→ role default) and `ask_downgrade` are `false`.
7. **`approved_decisions`** keeps applied `allow` and `deny` decisions (field `decision`), at most 10.
8. **`permission_target.bytes`** is the current size on disk (0 for a new file), not the size of the proposed content.

## Known limitations

- The TypeScript plugin was only parsed (Node 22 `stripTypeScriptTypes` + `new Function`). It was not type-checked:
  `make test-jev-sdk` needs the SDK from the network.
- AC-15 is not done: no R&D live run, no blackbox run, `verification.md` not updated (paid, out of this hand-off).
- D6: on Codex the `qa` default `gpt-6-terra` is not a tier candidate, so `qa` keeps its native model on fallback.
- Function-length violations that remain are pre-existing: `permission_boundaries` (non-goal), `api.run`,
  `api.answers_for`, `lint_prompts.main` / `check_skills`, `experiment.fixtures` / `main`.
- R&D fixtures override `state.repository` with a fixed snapshot, so results are reproducible. The runtime computes it
  from disk.

## Test evidence (2026-10-19, local, offline)

| Command | Result |
| --- | --- |
| `make test-jev-hooks` (gate 1, after increment 1) | 68 tests OK |
| `make lint` (gate 2) | rc 0 |
| `make test-unit test-integration` (gate 2) | 158 passed; 38 passed |
| `make lint-content test-content jev-rnd-verify` (gate 3) | rc 0; content 20 tests OK |
| `make lint` (final) | rc 0 (fmt, clippy `-D warnings`, version sync, content lint) |
| `make test` (final) | unit 158, integration 38, e2e 13, content 20, jev hooks 75, notify 11; all OK |
| `make jev-rnd-verify` (final) | rc 0, `summary.json` unchanged |
| `wc -l` | `questions.py` 383 (≤ 400), `hook.py` 445 (≤ 500); `routing.py` 186, `adapters.py` 186, `api.py` 299 |

Size evidence (AC-11): the real 73-workflow catalog with a 3840-character Cyrillic prompt is 25 001 bytes
(35 952 bytes if ASCII-escaped, which is over 32 KiB). The synthetic 80-workflow test passes. R&D fixture requests
are 2.3–5.9 KB.

## Iteration 2 (Scope change 1 and QA / team-lead findings)

### Changes

1. **QR-D4 / AC-8 amended:** `handle_permission` does not call JEV when `permission_boundaries` is false. The
   record has `status: fallback`, `reason_code: not_auto_allow_eligible`, `outcome: native`, `applied: false`,
   `decision: null` and `request: null`. Codex and Claude get `{}`; OpenCode gets no `decision`. `map_permission`
   still downgrades `allow` → `ask`; a direct unit test covers it, because the pipeline can no longer reach it.
2. **Team-lead P2s:**
   - (a) `_scan` checks the entry cap and the deadline per `os.scandir` entry, while reading.
   - (b) `permission_target` inspects only paths that resolve inside the project or the temp dir and do not match
     `SENSITIVE`. Outside paths, symlinks included, become `path: "[outside project]"` with `kind: outside`.
     Sensitive paths get `kind: secret_like`. Neither is stat-ed (`bytes`/`new_file` are `null`). Temp paths are
     shown as `$TMPDIR/…`. Kind `secret` is renamed `secret_like`.
   - (c) The `api` import is guarded. `load_runtime()` needs it, otherwise `runtime_incomplete`.
   - (d) `runtime_incomplete()` checks the JEV switch with stdlib JSON, because `api.py` may be the missing file.
     It then writes one record per event with identifiers only: host, kind, session, event and tool ids, no prompt
     and no input. `run_event` and the `codex_event`/`claude_event` wrappers use it when the runtime is partial, and
     the wrappers return `{}`.
   - (e) `Turn.request` keeps the sent request, so `request_failed` records keep the question when answer mapping
     raises.
3. **QR-D3:** `api.TOKEN` matches `jv_live_` / `ts_` / `sk-` only at a token start (`(?<![A-Za-z0-9_-])`) and only
   when the body has a digit. `tests_and_review_evidence`, `parts_inventory_service` and `ts_inventory_service`
   stay intact. Tokens such as `ts_live9aZk3QwErTy`, `sk-proj-Ab12…` and `jv_live_8f3k…` are still redacted.
4. **R&D questions suite:**
   - `experiment.py` now has two senders. `hook_client_sender` loads `api.py` by path and uses
     `api.hook_endpoint(settings)`, a new function that `api.evaluate` also uses, so the resolution is not
     duplicated. Endpoint: `JEV_API_URL` > `settings.jev.api_url` > official. Key: `TYPESAFE_API_KEY` for
     `api.typesafe.ai`, else `JEV_API_KEY`, through `api.key_for` (env or the repo `.env`).
   - The suite sends through `api.evaluate`. A missing key or a client fallback stops the run before any paid
     call, or at the first one.
   - The core suite still uses the hosted gateway.
   - If the API does not report a cost, the run records the admission estimate (`cost_reported: false`) instead of
     stopping, so `JEV_RND_BUDGET_USD` still caps the spend. `analyze.py` accepts `input_tokens: null`.
   - Not run (paid).
5. Docs: the README permission section, reason codes (`not_auto_allow_eligible`, wider `runtime_incomplete`), the
   threshold-floor note, the runtime guard, CHANGELOG and the R&D README.

### Deviations / limitations

- Through `api.evaluate`, the questions suite uses the hook timeout (8 s, `HOOK_TIMEOUT_SECONDS`), not the 30 s that
  the core suite uses.
- An `AGENTIC_JEV_BUDGET_FILE` ledger, if set, also applies to R&D calls.
- `runtime_incomplete` records cannot be scrubbed with `api.scrub` (it may be missing), so they hold only
  string-valued identifiers.

### Evidence (2026-10-19, offline)

| Command | Result |
| --- | --- |
| `make lint` | rc 0 |
| `make test` | unit 158, integration 38, e2e 13, content 20, jev hooks 82, notify 11; all OK |
| `make jev-rnd-verify` | rc 0; `summary.json` unchanged |
| `wc -l` | `questions.py` 398 (≤ 400), `hook.py` 489 (≤ 500), `api.py` 312 |

New or changed tests:
- `test_hooks.py`: `test_permission_limits_resist_even_confident_allow` (no call),
  `test_permission_state_is_metadata_only_and_keeps_decision_history` (eligible `ls`, skipped `&&` command),
  `test_confident_allow_still_downgrades_when_eligibility_is_lost`, `test_partial_runtime_writes_identifier_only_records`,
  `test_request_is_kept_when_answer_mapping_fails`.
- `test_questions.py`: outside/symlink/secret/temp targets, the per-entry deadline, `Redaction` (both directions).
- `test_rnd_fixtures.py`: `QuestionsSuiteClient` (endpoint and key reuse, missing key, client fallback).

## Iteration 3 (QA iteration 2 findings)

### Changes

1. **QR-D6 (AC-10):** `open_turn` labels spawn agents with the same rule as observations and permissions: an
   installed role (`.claude/agents`, `.codex/agents`, `.opencode/agents`) stays in `agent`; anything else becomes
   `agent: null` + `native_agent_type`. In `scripts/blackbox_jev.py`, `agent_label()` pairs a spawn with an
   observation by `session_id` and by `agent` or `native_agent_type`, so `Explore` is credited. Records written
   before QR-D6 still pair. The Codex test fixtures now install model-less `.codex/agents/*.toml`, as a real
   JEV-enabled install does.
2. **P1 / QR-D8:** `api.TOKEN` keeps the start-of-token boundary for every family.
   - `ts_` needs a digit.
   - `sk-` (also `sk-proj-` and `sk-ant-`) and `jv_live_` need a digit, or 20+ characters without one.
   - New families: `gh[pousr]_` with 20+ characters, `AKIA` with 16 characters, `xox[abprs]-` with 10+ characters.
3. **P2(c) direct test:** `test_missing_api_module_falls_back_with_runtime_incomplete` runs `hook.py` from a copied
   runtime without `api.py`, in a subprocess with no `PYTHONPATH`. It expects `runtime_incomplete` and one record
   with identifiers only.
4. **Docs:** the README explains that the ledger books $0.02 per call when no cost is reported, so the totals of
   `JEV_RND_BUDGET_USD` and the ledger differ ($0.092 vs $0.80 for 40 calls). The CHANGELOG is updated.

### Evidence (2026-10-19, offline)

| Command | Result |
| --- | --- |
| `make lint` | rc 0 |
| `make test` | unit 158, integration 38, e2e 13, content 20, jev hooks 86 (blackbox verify included), notify 11; all OK |
| `make jev-rnd-verify` | rc 0. `summary.json` now gains a `questions` section, because QA's paid `questions-results.json` exists (by design) |
| `wc -l` | `questions.py` 398 (≤ 400), `hook.py` 490 (≤ 500), `api.py` 319 |

New tests:
- `test_blackbox.py::test_native_helpers_are_matched_by_native_agent_type` (matches, a legacy record, mismatches).
- `test_claude_hooks.py::test_spawn_and_observation_label_agents_the_same_way`.
- `test_questions.py::Redaction` (two tests, both directions).
- `test_hooks.py::test_missing_api_module_falls_back_with_runtime_incomplete`.

## Iteration 4 (QR-D2 fix: AC-17 to AC-20, QR-D12, QR-D9)

Design: `notes-iteration4.md` §1–§3, with the PO decisions in §0a (AC-17 reworded, the I8 skip accepted, the
githubcopilot profile not changed).

### Catalog check (before any id edit, 2026-10-19)

- OpenCode 2.x rejects `opencode models openai` ("Unexpected positional argument"). I used
  `opencode models | grep '^openai/'` instead. It lists `openai/gpt-6-luna`, `openai/gpt-6.1-sol` and
  `openai/gpt-6-astra`. It does not list `gpt-6-terra` or `gpt-5-nano`.
- Codex `~/.codex/models_cache.json` (fetched_at 2026-10-19T07:58:31Z, client 0.163.0), `visibility: list`:
  `gpt-6.1-sol`, `gpt-6-astra`, `gpt-6-sol`, `gpt-6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`.

### Changes per file

| File | Change |
| --- | --- |
| `extensions/opencode/model-tiers.json` (new) | The v1 tier map from §1.1: `roles` (I4) and `providers.openai`. |
| `extensions/codex/hooks/jev/routing.py` (186 → 267) | New: `load_tier_map`, `provider_of`, `map_provider`, `tier_map_tiers`, `spawn_tiers`, `candidate_overrides`, `review_tier`, `opencode_role_default`, `plan_spawn`. `spawn_rule` takes `tiers` (reviewer fallback `tier_fast_price_unknown`). `role_default_model` now returns `(model, source)`; Codex/Claude behaviour unchanged. `candidates` is unchanged: every source other than `catalog_price` already gets rank cost 1/2/3, and a test now covers `tier_map`. |
| `extensions/codex/hooks/jev/hook.py` (490 → 484) | `OPENCODE_TIERS_FILE`. `handle_spawn` does I/O only: models, the tier map (OpenCode only, through `read_json`, which never raises), `routing.plan_spawn`, then `questions.model_request` when no `result`. Spawn records get top-level `cost_source` and `role_default_source`. |
| `extensions/opencode/hooks/agentic-jev.ts` (170 → 174) | `setup` reads `.agent/jev/opencode-model-tiers.json` once, with its own `catch` → `{}` (not `readConfig`). The pool is role models ∪ every string under `providers.*`; the catalog, `capabilities.tools` and provider filters are unchanged. |
| `src/jev_hooks.rs` (466 → 465) | New asset `.agent/jev/opencode-model-tiers.json` (`include_str!`), source arm, `OPENCODE_ONLY` list for the `wanted` condition (same condition as the profile defaults). The profile-defaults block moved out. |
| `src/jev_defaults.rs` (123 → 185) | `OPENCODE_TIERS_SOURCE`, `opencode_profile_defaults(app)`, three unit tests. |
| `src/copydir.rs` | `model-tiers.json` is skipped for both `extensions/codex` and `extensions/opencode`, so `.opencode/model-tiers.json` is never written. |
| `extensions/opencode/profiles/openai/opencode.json` | §1.6: `openai/` prefixes; developer → `openai/gpt-6.1-sol` with fallback `openai/gpt-6-astra`; `small_model` → `openai/gpt-6-luna`. |
| `extensions/codex/agents/qa.toml` | `model = "gpt-6.1-sol"` (D6). `roles.qa` in `model-defaults.json` follows; `hooks.json` and the trust hashes are unchanged. |
| `scripts/blackbox_jev.py` | `run_root(args)` returns `args.run_dir.resolve()` (QR-D9). |
| Docs | `docs/jev-integration/README.md` (tier map, role-tier defaults, `assignment_unavailable`, `tier_fast_price_unknown`, the two new record fields); `notes.md` §3 "superseded" line; `CHANGELOG.md` 1.4.0 bullets and an operational note; the guidance-update note; the root `README.md` model-routing bullet. The TG-HDR bullets are unchanged. |

### Tests

- `tests/jev/test_opencode_tiers.py` (new, 15 tests) covers §3 items 1–11. Items 1–4: tier source for no, partial,
  equal and distinct prices. Item 5: catalog gaps (fast and balanced only, `single_eligible`, `no_tier_routing` with
  the profile default). Also an override-only case. Item 6: provider choice (env, role-default provider, file order,
  never mixed). Item 7: role default (`profile`, the `gpt-6-terra` → `role_tier`, none, unmapped, native `explore`,
  Codex/Claude unchanged). Item 8: pins. Item 9: the reviewer fast tier. Item 11: malformed maps, as a unit test and
  through `hook.run_event`. Item 10: end to end through `hook.run_event`, `clarify` 0.5 → `openai/gpt-6.1-sol`
  `role_default`/`role_tier`, and `fast` 0.95 → `openai/gpt-6-luna` `jev_tier`.
- `tests/jev/test_hooks.py::test_codex_encrypted_assignment_skips_jev_and_applies_role_default` covers item 12.
  `evaluate` is set to `side_effect=AssertionError`. The same test sends a plain assignment, which is still asked.
  The OpenCode and Claude "still asks" paths are covered by the end-to-end test and
  `test_claude_hooks.py::test_confident_tiers_map_to_aliases`. Negative check: with the skip removed, this test fails.
- `tests/jev/test_blackbox.py::RunRoot` covers item 13.
- Rust: `jev_defaults::tests::{codex_role_defaults_are_tier_models, opencode_profile_defaults_follow_the_selected_profile, opencode_install_writes_the_tier_map_verbatim}`.
  `tests/cli.rs::jev_hooks_enable_provider_replay_and_explicit_disable` checks the tier file (byte-equal to the
  source), `opencode-profile-defaults.json == {}`, no `.opencode/model-tiers.json`, and removal after `--disable-jev`.
- `tests/content/test_model_ids.py` (new, 5 tests): frozen catalogs, profile ids, tier-map ids, Codex role and tier
  ids, OpenCode/Codex role-tier parity, `roles` keys, and no `gpt-6-terra` outside `profiles/githubcopilot/`.

### Evidence (2026-10-19, offline)

| Command | Result |
| --- | --- |
| `make lint` | rc 0 |
| `make test` | rc 0. Unit 161, integration 38, e2e 13, content 25, jev hooks 103, notify 31; all OK |
| `make jev-rnd-verify` | rc 0. `summary.json` is regenerated with no timestamps, and its inputs are unchanged |
| `wc -l` | `hook.py` 484 (≤490), `questions.py` 398 (not edited: untracked, and its mtime is older than every iteration-4 edit), `routing.py` 267 (≤400), `agentic-jev.ts` 174 (≤400), `jev_hooks.rs` 465 (≤466), `jev_defaults.rs` 185 (≤400) |
| `ast` scan, new or changed functions | 0 functions over 30 lines. Longest: `plan_spawn` 17, `hook.main` 22 (unchanged), test helpers ≤19 |
| Plugin syntax | `node --experimental-strip-types --check` rc 0 (make has no TS gate) |

`make blackbox*` was not run: the paid AC-19 run is QA's job after review. `verification.md` gets its iteration-4
section after that run.

### Deviations

- **The tier-map tests are in a new `tests/jev/test_opencode_tiers.py`, not in `test_questions.py`/`test_hooks.py`.**
  `test_hooks.py` was already 454 lines, above the ~400-line file guideline. Only the Codex QR-D12 test, which uses
  that file's fixtures, went into `test_hooks.py` (now 474 lines).
- **The catalog command is `opencode models | grep '^openai/'`.** `opencode models openai` is rejected by the
  installed OpenCode 2.x.
- **`cost_source` for override-only tiers.** When no prices and no map apply but `settings.jev.tiers` overrides
  give tiers, `cost_source` is `tier_order` (rank cost), not `null`. A `null` source with candidates would be
  ambiguous, and the old `catalog_price` label claimed prices that did not exist.
- **Native agents and role tiers.** `label_agent` sets `agent: null` for native helpers. So `opencode_role_default`
  also looks up `native_agent_type`; without it, the `explore`/`general` map entries could never match.
- **`role_default_source` for rule outcomes.** Pinned, single-eligible, reviewer and configuration-unavailable
  spawns record `role_default_source: null`, because no role default is resolved or applied. `cost_source` is still
  recorded for them.
- **`role_default_model` signature.** It now returns `(model, source)`. Its only caller is `routing.plan_spawn`.

### Limitations

- The tier map has only `openai` (I7, follow-up F1). Anthropic and GitHub Copilot users on OpenCode keep the
  price-only behaviour. The Copilot profile still names `gpt-6-terra` (F1, PO decision).
- The frozen catalogs in `test_model_ids.py` are a snapshot. A host catalog change needs a manual refresh.
- In the plugin, a non-object `providers` value can add junk strings to the pool. They are harmless: the catalog
  filter removes them.
- R3 is still open: QA must check that `explore`/`general` are the real OpenCode 2.0.29 agent ids in the paid run.

## Iteration 4a (team-lead review: P2-1, P3-1, P3-4)

### Changes

- **P2-1:** `routing.map_provider` no longer falls back to file order when a provider is preferred.
  - A preferred provider (`AGENTIC_JEV_MODEL_PROVIDER`, else the role-default prefix) must qualify itself; otherwise
    the result is `None` and there are no map tiers.
  - File order applies only without a preference.
  - So a `github-copilot/x` role default with OpenAI map models in the catalog gives `no_tier_routing`, and the role
    default applies.
  - Tests:
    - new `test_opencode_tiers.py::ProviderChoice::test_role_on_an_unmapped_provider_never_routes_to_map_models`;
    - `test_providers_are_never_mixed` now expects `{}` for a non-qualifying preferred provider, and file order without a preference.
- **P3-1:** the QR-D12 skip in `plan_spawn` checks `event.get('host') == 'codex'`.
  - New test: `test_opencode_tiers.py::EndToEnd::test_opencode_spawn_with_assignment_unavailable_still_asks`.
- **P3-4:** the `CHANGELOG.md` operational note says to restart OpenCode after a reinstall, because the plugin reads
  the tier map at setup.
- **Docs:** the `docs/jev-integration/README.md` provider rule and the Codex-only QR-D12 rule are updated. The
  CHANGELOG tier-map bullet notes that a role on an unmapped provider gets no map tiers.

### Negative checks

- The P2-1 test fails with the old `map_provider`.
- The P3-1 test fails with the old host-less skip.
- Both pass with the fix.

### Evidence (2026-10-19, offline)

| Command | Result |
| --- | --- |
| `make test-jev-hooks` | rc 0, 105 tests |
| `make test-content` | rc 0, 25 tests |
| `make lint` | rc 0 |
| `make test` | rc 0: unit 161, integration 38, e2e 13, content 25, jev hooks 105, notify 31 |
| `wc -l` | `routing.py` 270 (≤400), `hook.py` 484 (≤490); `map_provider` is 8 lines |

### Follow-ups (backlog, not in scope)

- **P3-2:** the frozen catalogs in `tests/content/test_model_ids.py` reflect the `opencode models` listing, not OAuth
  usability. A listed model can still be rejected at request time. R1 and the availability cooldown cover this at
  runtime.
- **P3-3:** the `catalog_price` path (`opencode_tiers`) does not enforce a single provider. Fully priced, mixed-provider
  pools can still mix providers.
- **P3-5:** `tests/jev/test_hooks.py` is 474 lines, above the ~400-line guideline; split it by host or by question.
