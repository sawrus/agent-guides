# JEV-QR — Technical design (team-lead)

Status: APPROVED (team-lead, 2026-10-18). D1–D7 are binding.
PO decisions (2026-10-19): D1 accepted — Codex `frontier = gpt-6-astra`; D2–D7 accepted; D3 and D6 logged as follow-ups.

## 1. Module layout

`extensions/codex/hooks/jev/questions.py` — stdlib only, `VERSION = 2`, ≤400 lines, functions ≤30 lines.

- **Frontmatter:**
  - `front_block(text) -> str | None`.
  - `parse_front(text) -> dict` (scalars, `- item` lists, one-level nested maps: `execution`, `selection`).
- **Workflows:**
  - `parse_workflow(path, project) -> dict | None` (`None` unless `type: workflow`).
  - `workflow_criterion(w, level) -> str`. Level 0 is full; levels 1–3 drop roles, then inputs/outputs, then truncate `use-when`.
  - `fit_criteria(catalog, budget=20000) -> dict`. Adds `native` and `clarify`.
- **State helpers:**
  - `repo_snapshot(project, max_entries=5000, max_depth=6, seconds=.3) -> dict`.
  - `installed_areas(manifest) -> list`.
- **Request builders:**
  - `workflow_request(prompt, catalog, project, manifest)`.
  - `model_request(role_ctx, candidates, workflow, original)`.
  - `permission_request(event, project, context, eligible)`.
- **Tiers and prices:**
  - `load_defaults(project) -> {"roles", "tiers"}` (v2 and the legacy flat format).
  - `price(cost) -> float | None` (dict or list).
  - `opencode_tiers(models)`.
  - `candidates(models, tiers, cost_source)`.
- **Permission metadata:** `path_kind(path)`, `permission_target(project, raw)`, `command_meta(command)`.
- **Thresholds:** `threshold(settings, name) -> float`.

`hook.py` keeps:
- I/O: `read_json`, `scrub`, `private_dir`, `save_json`;
- budget handling and `evaluate`;
- `permission_boundaries` and `bounded_path` (unchanged, non-goal);
- `review_packet`, the Codex and Claude adapters, and `main`.

`run_event` is split into `handle_prompt`, `handle_spawn`, `handle_permission`, `apply_answer` and `finish_record`. Delete `claude_session_model`, `workflow_catalog` and the instruction literals.

Guarded import (`api` and `questions` share the script directory, `sys.path[0]`):

```python
try:
    import questions
    if getattr(questions, 'VERSION', 0) != 2: questions = None
except (ImportError, SyntaxError):
    questions = None
```

After the `disabled` check, `run_event` returns `fallback/runtime_incomplete` when `questions is None`.

## 2. Data shapes and records

- **Workflow state:**
  - `original_request` (≤3000) and `original_request_truncated`;
  - `installed_areas`;
  - `repository: {is_git, source_files, top_languages, has_makefile, has_ci, only_agent_guidance, truncated}`;
  - no catalog.
  - The snapshot uses `os.scandir` and does not follow symlinks. It skips `.git`, `node_modules`, `target`, `.venv`, `.agentic*`.
- **Model state:**
  - fields as in AC-5, plus `original_request` and `assignment_unavailable`;
  - `relative_cost` is tier rank 1/2/3 with `cost_source: "tier_order"` (Claude, Codex), or `price/min_price` with `"catalog_price"` (OpenCode).
- **Permission state:**
  - fields as in AC-8;
  - `approved_decisions`: the last 10 `{action, targets, decision}`, kept in `context-*.json`.
- **`model-defaults.json` v2:** `{"version": 2, "roles": {role: model}, "tiers": {"fast"|"balanced"|"frontier": model}}`.
- **`.agentic.json` `settings.jev`:**
  - `thresholds: {workflow, model, permission}`;
  - `lightweight_model`;
  - `tiers` (an override counts only if its model is a candidate).
- **Reason codes:**
  - new: `native_request`, `clarification_needed`, `runtime_incomplete`, `no_tier_routing`;
  - removed: `no_matching_workflow`.
- **Record fields (D4):** these go at the top level of `event-*.json`, not inside `result`, because `result.decision` is the adapter and plugin contract.
  - `decision` (raw JEV choice or `null`);
  - `threshold`;
  - `applied` (bool);
  - `outcome`: `jev_applied | role_default_applied | rule_applied | ask_downgrade | native`;
  - `tier`;
  - `model_source`: `jev_tier | role_default | single_eligible | review_model | pinned | none`.
- Spawn results also carry `tier` and `model_source`.
- `profile_default` is renamed to `role_default`. Update the Claude `permissionDecisionReason` and the test at `test_claude_hooks.py:161`.
- Add `'v': 2` to the identity hash.

### Compatibility with `scripts/blackbox_jev.py verify`

The script reads these fields; they keep their meaning:
- `context.{kind, prompt, session_id, task_id, agent}`;
- `result.workflow.{id, path}` with `status == "evaluated"`;
- tool `resources`;
- spawn `result.model` with `status == "evaluated"`, matched to the observation `result.observed_model` by the same `session_id` and `agent`.

Rules that follow from this:
- The record `context` stays the scrubbed event, with `prompt` unchanged. Truncation applies to `state` only.
- `result.model` is the concrete model, never the tier name.
- A role-default fallback stays `status: fallback`. It is not counted as `model_applied`; this is expected.
- `result.workflow` gains `roles` and keeps `initiator` (`execution.initiator`, else `agent`).

## 3. Tier mapping per host

- **Claude:**
  - `extensions/claude/profiles/anthropic/profile.json` gets `"tiers": {"fast":"haiku","balanced":"sonnet","frontier":"opus"}`;
  - new `claude::profile_tiers(app)`, mirroring `profile_models`;
  - if tiers do not resolve to aliases (combined claude+codex install, D7), the hook uses the same built-in alias map.
- **Codex:**
  - new `extensions/codex/model-tiers.json`: `{"fast":"gpt-6-luna","balanced":"gpt-6.1-sol","frontier":"gpt-6-astra"}`;
  - the `codex_models` pool becomes roles ∪ tiers, intersected with the catalog.
- **OpenCode:** superseded by `notes-iteration4.md` (tier map, hook-side role defaults).
  - the plugin drops `default_model`;
  - on spawn it sends `role_default: refID(agent?.model) ?? profileDefaults[input.agent]` and `prices: m.cost`;
  - on permission it sends `agent: (await ctx.session.get(...)).agent`;
  - the hook sorts priced candidates: 2 → fast and frontier; 3 or more → fast = cheapest, frontier = most expensive, balanced = lower median;
  - any unknown price, or all prices equal, gives no tiers: `fallback/no_tier_routing` and the role default.

The role-default fallback applies on all hosts to any spawn fallback, except pinned/preserved spawns and `project_configuration_unavailable`.

## 4. Increments

1. **Python runtime**
   - `questions.py`, the `hook.py` refactor, `tests/jev/test_questions.py`;
   - updates to `test_hooks.py` and `test_claude_hooks.py` (fixtures need `type: workflow`);
   - gate: `make test-jev-hooks`.
2. **Installer and plugin**
   - `questions.py` asset, with its own `source` match arm;
   - v2 defaults in a new `src/jev_defaults.rs` (`jev_hooks.rs` is already 473 lines);
   - `model-tiers.json` and `profile_tiers`;
   - `manifest.rs:404` keeps `thresholds`, `lightweight_model` and `tiers` from `old_settings["jev"]`;
   - `tests/cli.rs:99` and `:1209` move to `["roles"]` and `["tiers"]`;
   - TypeScript plugin;
   - gates: `make lint`, `make test-unit test-integration`.
3. **Content, R&D and docs**
   - `selection` after `agent:` in all workflows; `general: true` only in `software/general/development-cycle-workflow`;
   - `check_workflows` in `lint_prompts.py` imports the parser from `questions.py`. Rules: at most one `general: true` per top-level area; `use-when` non-empty, ≤300 chars;
   - R&D fixtures in `docs/jev-rnd/question_fixtures.py`, results in `docs/jev-rnd/questions-results.json`;
   - `analyze.py` validates the results file when present and accepts a set of expected labels;
   - eval cases must not use "calculator" (held-out test);
   - docs and CHANGELOG;
   - gates: `make lint-content test-content jev-rnd-verify`.

## 5. Quality gates and QA

- **Gates:**
  - `make lint`, `make test`, `make jev-rnd-verify`;
  - `wc -l`: `questions.py` ≤400, `hook.py` ≤500 (D3);
  - AC-11 offline size test, sent with `ensure_ascii=False`.
- **Paid runs, in this order:**
  1. **R&D:** `JEV_RND_SUITE=questions JEV_RND_BUDGET_USD=0.15 make -f docs/jev-rnd/Makefile live`, then `make jev-rnd-verify`.
  2. **Codex:** `BLACKBOX_CODEX_SANDBOX=danger-full-access make blackbox-codex` (bwrap cannot create user namespaces on this machine).
     - If the run is blocked with "hooks need review", the user trusts the hooks in `codex` → `/hooks`.
     - Then rerun with `BLACKBOX_ARGS="--run-dir .agentic-blackbox/<ts>"`.
  3. **OpenCode:** `make blackbox-opencode` (`openai/gpt-6-luna`).
  4. **Claude:** `make blackbox-claude`.
  - To recheck offline: `BLACKBOX_ARGS="--verify-only --run-dir …"`.
- **Budget:**
  - keep `.agentic-blackbox/jev-budget.json` ($1.94 of $5 committed, so $3.06 headroom);
  - record the `committed_usd` delta.
- **Evaluation per host** (from `results.json` and `.agentic/jev/event-*.json`):
  - questions per kind;
  - applied vs fallback (baseline 2/11);
  - `outcome`, `model_source`, reason codes;
  - observed models;
  - the developer must not get opus on Claude;
  - a host blocked by a manual step is recorded with the reason.

## 6. Risks and decisions

- **D1.** Codex tiers: the plan said to use only slugs already in use. `gpt-6-terra` is not in the catalog, so `frontier = gpt-6-astra`. Accepted by the PO.
- **D2.** The AC-1 runtime check covers only `request.questions` and the hook's injected context. `state` holds user and coordinator text, which may say "calculator".
- **D3.** `hook.py` will be about 500 lines after the refactor, above the 400-line guideline. Splitting the adapters out is a P2 follow-up.
- **D4.** The record fields go at the top level (see §2).
- **D5.** Keep the existing budget file; measure AC-15 as a delta.
- **D6.** On Codex, the qa default `gpt-6-terra` is not a candidate, so qa keeps its native model on fallback. P1 follow-up, out of scope.
- **D7.** A combined claude+codex install writes one `model-defaults.json`: Codex wins, Claude uses the built-in alias tiers. P2.
- **Behaviour risks:**
  - an empty repository may pull a build request to project-setup;
  - the developer may be routed to `fast`;
  - the R&D families must show acceptable agreement before the blackbox runs; otherwise stop and tune the rubric.
- **Threshold floor:** a permission threshold of 0.5 is safe only because `auto_allow_eligible` still applies. The docs must say so.
- **`selection` blocks:** `sync_workflow_diagrams` and `build_docs_catalog` use regex parsing. `lint-content` must stay green after the blocks are added.
