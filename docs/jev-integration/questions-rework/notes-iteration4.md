# JEV-QR iteration 4 — QR-D2 fix design (team-lead)

**Status:** APPROVED. Team-lead design, 2026-10-19; product-owner decisions in §0a.

**Covers:**
- AC-17 to AC-20 (Scope change 2);
- QR-D10, QR-D11, D6, QR-D12 and QR-D9.

D1 to D7 in `notes.md` stay binding. For OpenCode, this note replaces `notes.md` §3.

## 0. Decisions

| ID | Decision |
|:---|:---|
| I1 | Tier and role-default resolution runs in the **hook** (`routing.py`). The plugin only widens the model pool. In a default install, the raw plugin `context.role_default` stays `null`. The resolved `request.state.role_default.model` and the fallback `result.model` are non-null. |
| I2 | Candidates = host catalog (tool-capable) ∩ (installed role models ∪ every model in the shipped tier map). Tiers come from **one provider only**. |
| I3 | Tier source, in order. (1) Runtime prices, when every pooled model is priced and min ≠ max → `catalog_price`. (2) Otherwise the tier map filtered to the catalog, if ≥2 tiers remain → `tier_map`. (3) Otherwise no tiers → `fallback/no_tier_routing`. `settings.jev.tiers` overrides still apply on top and must be candidates. |
| I4 | Role tiers mirror the Codex role defaults. `balanced`: product-owner, team-lead, developer, qa, devops-engineer, and native `general`. `fast`: analyst, pm, instruction-reviewer, memory-curator, and native `explore`. Frontier is never a role default; JEV may still pick it with confidence. A content test enforces parity with Codex. |
| I5 | Explicit pins stay authoritative: `input.model`, Markdown `model:`, root `opencode.json(c)`, and a user-changed `.opencode/opencode.json`. They go through `spawn_rule` → `preserved`. A profile role model (`opencode-profile-defaults.json`) wins over the role tier only when it is in the catalog. Otherwise the role tier applies. |
| I6 | AC-20 changes: fix `profiles/openai/opencode.json` (§1.6); set Codex `qa.toml` → `gpt-6.1-sol` (balanced). **The githubcopilot profile is not changed** (see §0a). |
| I7 | The tier map has no `anthropic` or `github-copilot` entry: neither catalog is verified. Follow-up F1. |
| I8 | QR-D12: on a spawn with `assignment_unavailable: true` (Codex), the hook does not ask JEV. It returns `fallback/assignment_unavailable` and applies the role default. |
| I9 | QR-D9: `scripts/blackbox_jev.py` resolves `--run-dir` to an absolute path, via `run_root(args)`. |
| I10 | `questions.py` (398/400) is not changed. `cost_source: "tier_map"` is a new value of an existing state field. `relative_cost` for `tier_map` is the tier rank 1/2/3. No R&D re-run is needed. |

## 0a. Product-owner decisions (2026-10-19)

- **I1: accepted.** AC-17 is reworded: "A default OpenCode install resolves a default model for every installed role. The spawn request `state.role_default.model` and the fallback `result.model` are non-null, and the model question has ≥2 candidates." The raw plugin `role_default` may stay `null`.
- **I8: accepted.** AC-6 is amended: "clarify, low confidence, an API error, or an unavailable (encrypted) assignment → role default". Rationale: 4/4 `clarify` at 0.40–0.60; the call cannot change the outcome. This is the same reasoning as Scope change 1. The change is reversible, and the reason code keeps it visible.
- **I6, githubcopilot: not accepted in this scope.** The Copilot catalog is not verified, so the content `gpt-6-terra` ban excludes `extensions/opencode/profiles/githubcopilot/`. The Copilot `gpt-6-terra` is added to follow-up F1.

## 1. Files to change

### 1.1 New `extensions/opencode/model-tiers.json`

```json
{
  "version": 1,
  "roles": {
    "product-owner": "balanced", "team-lead": "balanced", "developer": "balanced",
    "qa": "balanced", "devops-engineer": "balanced",
    "analyst": "fast", "pm": "fast", "instruction-reviewer": "fast", "memory-curator": "fast",
    "explore": "fast", "general": "balanced"
  },
  "providers": {
    "openai": {"fast": "openai/gpt-6-luna", "balanced": "openai/gpt-6.1-sol", "frontier": "openai/gpt-6-astra"}
  }
}
```

- Ids are always `provider/id`.
- The order of `providers` in the file is significant: it is the tie-break in §2.

### 1.2 `extensions/codex/hooks/jev/routing.py` (≤400 lines, functions ≤30 lines)

**New pure functions**
- **`load_tier_map(data)`** → `{'roles', 'providers'}`. It returns empty maps unless `version == 1`. It keeps only the `TIERS` keys and string values, and it never raises.
- **`map_provider(tier_map, ids, preferred)`** chooses the provider from those with ≥2 tier models in `ids`. It returns `preferred` if that provider qualifies, otherwise the first qualifying one in file order, otherwise `None`.
- **`tier_map_tiers(tier_map, models, preferred)`** → `{tier: id}` for the chosen provider, restricted to catalog ids, or `{}`.
- **`spawn_tiers(event, models, defaults, overrides, tier_map)`** → `(tiers, cost_source)`.
  - Claude and Codex: unchanged (`host_tiers`, `tier_order`).
  - OpenCode: `opencode_tiers(models)` → `catalog_price`. Otherwise `tier_map_tiers` → `tier_map`. Otherwise `({}, None)`. The candidate-only overrides apply in each case.
  - `preferred` = `AGENTIC_JEV_MODEL_PROVIDER`, otherwise the provider prefix of `event.role_default`.
- **`opencode_role_default(event, tiers, role_tiers, ids)`**:
  - explicit `event.role_default` in `ids` → `(m, 'profile')`;
  - otherwise `tiers.get(role_tiers.get(role))` → `(m, 'role_tier')`;
  - otherwise `(None, None)`.
- **`plan_spawn(event, models, defaults, settings, tier_map)`** collects what `hook.handle_spawn` builds today: `spawn_rule`, tiers, role default, pool, the `no_tier_routing` check and the QR-D12 skip. It returns `{tiers, role_default, fields: {cost_source, role_default_source}, result?}`, plus `role_ctx` and `pool` when a question is needed.

**Changed functions**
- **`candidates`:** `tier_map` uses rank cost, like `tier_order`. Add a test for it.
- **`spawn_rule(event, settings, models, tiers=None)`:** the instruction-reviewer path gets a last fallback. When `review_model` finds nothing, use `tiers['fast']` with reason `tier_fast_price_unknown` and `model_source: review_model`.
- **`role_default_model`:** Codex and Claude are unchanged. OpenCode delegates to `opencode_role_default`.

### 1.3 `extensions/codex/hooks/jev/hook.py` (490, no net growth)

- **New constant:** `OPENCODE_TIERS_FILE = Path('.agent/jev/opencode-model-tiers.json')`.
- **`handle_spawn` becomes I/O plus delegation:**
  - `spawn_models`;
  - `tier_map = routing.load_tier_map(read_json(...))`, for OpenCode only;
  - `plan = routing.plan_spawn(...)`;
  - if the plan has no `result`, call `questions.model_request(plan['role_ctx'], plan['pool'], ..., cost_source)`.
- **Spawn records** get top-level `cost_source` (`catalog_price | tier_map | tier_order | null`) and `role_default_source` (`profile | role_tier | defaults | null`). The existing `status`, `model`, `outcome` and `model_source` fields keep their meaning.
- **Failure mode:** a missing, unreadable or malformed tier map gives today's behaviour and never raises.

### 1.4 `extensions/opencode/hooks/agentic-jev.ts`

- **In `setup`:** read `.agent/jev/opencode-model-tiers.json` once, with its own `catch` → `{}`. Do not use `readConfig`, so that a bad map does not set `configuration_unavailable`. `tierModels` = all string values under `providers.*`.
- **Pool:** `new Set([...roleModels, ...tierModels])`. The existing filter stays: catalog membership, `capabilities.tools`, `AGENTIC_JEV_MODEL_PROVIDER`.
- **No other changes:** `role_default`, pins and the permission and observation hooks stay as they are.

### 1.5 Installer (Rust)

**`src/jev_hooks.rs`** (466 lines, no net growth):
- Add the asset `(".agent/jev/opencode-model-tiers.json", include_str!("../extensions/opencode/model-tiers.json"))`.
- Make it `wanted` under the same condition as `opencode-profile-defaults.json`.
- Add the source arm.
- Move the `opencode_defaults` block (about lines 284–297) into `jev_defaults.rs` as `pub fn opencode_profile_defaults(app) -> Value`.

**Other files:**
- `src/jev_defaults.rs`: add the const `OPENCODE_TIERS_SOURCE`.
- `src/copydir.rs:41`: also skip `extensions/opencode/model-tiers.json`, so it is not copied into `.opencode/`.
- Managed-file cleanup when JEV or OpenCode is deselected goes through the existing loop. Cover it with a test.

### 1.6 Content

**`extensions/opencode/profiles/openai/opencode.json`**
- `gpt-6.1-sol` → `openai/gpt-6.1-sol` for product-owner, team-lead, devops-engineer, plan and build.
- Fallbacks `gpt-6-astra` → `openai/gpt-6-astra`.
- developer: `openai/gpt-6-terra` → `openai/gpt-6.1-sol`, with fallback `["openai/gpt-6-astra"]`.
- `small_model`: `openai/gpt-5-nano` → `openai/gpt-6-luna`. Re-check with `opencode models openai` before editing.

**Other files**
- `extensions/codex/agents/qa.toml`: set `model = "gpt-6.1-sol"`. `roles.qa` in `model-defaults.json` follows. `hooks.json` and the Codex trust hashes do not change.
- `scripts/blackbox_jev.py`: `run_root(args)` returns `args.run_dir.resolve()`, so the derived `AGENTIC_CONFIG_DIR` is absolute.

### 1.7 Docs (same change set)

- **`docs/jev-integration/README.md`:**
  - OpenCode tier source: `catalog_price`, otherwise `tier_map`;
  - role-tier defaults;
  - reason code `assignment_unavailable`;
  - reviewer `tier_fast_price_unknown`.
- **`questions-rework/scope.md`:** the AC-17 wording and AC-6 amendment are already applied by the PO.
- **`notes.md` §3 OpenCode:** add one line, "superseded by notes-iteration4.md".
- **`CHANGELOG.md` 1.4.0:**
  - OpenCode tier map and role defaults;
  - profile id fixes;
  - Codex qa default;
  - the Codex skip on encrypted assignments;
  - an operational note: OpenCode users with a custom profile keep their explicit catalog models.
- **`docs/guidance-updates/2026-10-19-jev-questions-rework.md`:** amend it.
- **`verification.md`:** add an iteration-4 section after the paid run.

## 2. Rule (normative)

```
OpenCode spawn:
  models   = catalog ∩ tool-capable ∩ (role models ∪ tier-map models) [∩ AGENTIC_JEV_MODEL_PROVIDER]
             minus models in availability cooldown
  rule     = configuration_unavailable → fallback (keep native)
             pinned / continuation     → preserved (keep native)
             |models| == 1             → single_eligible
             instruction-reviewer      → lightweight / cheapest priced / tier fast
  tiers    = price tiers if all priced and min ≠ max         → cost_source catalog_price
             else tier map of provider P with ≥2 catalog hits → cost_source tier_map
             else {}                                          → no_tier_routing
             (+ settings.jev.tiers overrides that are candidates)
             P = AGENTIC_JEV_MODEL_PROVIDER | provider(role_default) | first qualifying in file order
  default  = explicit role_default ∈ models → source profile
             else tiers[role_tiers[role]]    → source role_tier
             else null                       → native (model_source none)
  ask JEV  when |candidates| ≥ 2 and not assignment_unavailable
  answer   confident tier → jev_tier; anything else → role_default_applied (status fallback)
Codex/Claude: unchanged except the QR-D12 skip (Codex sets assignment_unavailable).
```

## 3. Tests

**Python** (`tests/jev/test_questions.py`, `test_hooks.py`, `test_blackbox.py`)

1. All map models have `cost: []` → `tier_map`, 3 candidates, `relative_cost` 1/2/3.
2. Partial prices → `tier_map`.
3. Equal prices → `tier_map`.
4. Complete, distinct prices → `catalog_price` (regression).
5. Map model missing from the catalog:
   - astra missing → fast and balanced only;
   - only luna → `single_eligible`;
   - luna plus an unrelated role model → `no_tier_routing` with the explicit role default.
6. Provider choice:
   - the env var wins;
   - the role-default provider is preferred;
   - otherwise file order;
   - providers are never mixed (two-provider fixture).
7. Role default:
   - explicit and in the catalog → `profile`;
   - explicit `openai/gpt-6-terra` → `role_tier` balanced;
   - none → `role_tier`;
   - role not in the map → `null` / native;
   - Codex and Claude unchanged.
8. Pins (`input.model`, Markdown `model:`) → `preserved`; no role default is applied.
9. instruction-reviewer with no lightweight model and no prices → `tiers.fast`, `tier_fast_price_unknown`, no JEV call.
10. End to end through `hook.run_event`, default-install event (`role_default: null`, the 3 unpriced map ids, agent `developer`):
    - state: `cost_source == 'tier_map'`, 3 candidates, `role_default == {model: openai/gpt-6.1-sol, tier: balanced}`;
    - `clarify` at 0.5 → `openai/gpt-6.1-sol`, `model_source: role_default`, `role_default_source: role_tier`;
    - `fast` at 0.95 → `openai/gpt-6-luna`, `jev_tier`.
11. Tier map missing, malformed, or `version: 2` → no exception; today's behaviour.
12. QR-D12:
    - Codex spawn with `assignment_unavailable` → `evaluate` is not called (`side_effect=AssertionError`); `fallback/assignment_unavailable`; role default applied;
    - an OpenCode or Claude spawn without the flag still asks.
13. `run_root` turns a relative `--run-dir` into an absolute path, and `AGENTIC_CONFIG_DIR` is absolute.

**Rust**
- Default OpenCode install:
  - writes `.agent/jev/opencode-model-tiers.json`, byte-equal to the source plus the marker;
  - `opencode-profile-defaults.json == {}`.
- Disabling JEV removes the tiers file.
- `.opencode/model-tiers.json` is not created.
- `roles.qa == "gpt-6.1-sol"`, and every Codex role model is a `tiers` value.
- `tests/cli.rs`: the OpenCode install has the tiers file.

**Content** (new `tests/content/test_model_ids.py`)
- Frozen catalogs, captured and dated in the docstring:
  - OpenCode openai: `opencode models openai`;
  - Codex: `~/.codex/models_cache.json` slugs with `visibility: list`.
- Every `model`, `fallback[]` and `small_model` in `profiles/openai` is in the OpenCode openai catalog and has the `openai/` prefix.
- Every value under tier map `providers.openai` is in that catalog.
- Every `extensions/codex/agents/*.toml` model and every `extensions/codex/model-tiers.json` value is in the Codex catalog. Every Codex role model is a Codex tier value.
- Parity: the OpenCode `roles[role]` equals the tier of the Codex role model.
- `roles` keys ⊆ installed role agents ∪ {`explore`, `general`}.
- No `gpt-6-terra` anywhere under `extensions/`, **except** `extensions/opencode/profiles/githubcopilot/` (PO decision, F1).

## 4. Quality gates (all through make, rc 0)

- **Make targets:** `make lint` and `make test`. This includes `test-jev-hooks`, `test-content`, `lint-content`, the Rust tests and `test-notify`. Also run `make jev-rnd-verify`.
- **Line counts (`wc -l`):**

  | File | Limit |
  |:---|:---|
  | `hook.py` | ≤490 |
  | `questions.py` | 398, unchanged |
  | `routing.py` | ≤400 |
  | `agentic-jev.ts` | ≤400 |
  | `jev_hooks.rs` | ≤466 |
  | `jev_defaults.rs` | ≤400 |

- **Function length:** ≤30 lines for every new or changed Python function, checked with an `ast` scan.
- **AC-1:** the grep test still passes.
- **Paid run (§5):** only after all offline gates are green and team-lead has reviewed the diff.

## 5. Paid OpenCode blackbox plan (AC-19)

**Budget**
- Ledger at $3.32 of $5.
- Expected cost: $0.10–0.30.
- Hard ceiling: `committed_usd` ≤ $3.92.

**Pre-flight (free)**
1. `opencode models openai` still lists luna, 6.1-sol and astra.
2. Check the ledger.
3. Confirm no other harness run is active.

**Run:** `make blackbox-opencode`, default install (no `AGENTIC_OPENCODE_PROFILE`).

**Evidence**

| Check | Expected |
|:---|:---|
| Profile defaults | `opencode-profile-defaults.json == {}` |
| Plugin context | `context.models` has ≥2 openai ids with `prices: []`; `context.role_default` is `null` |
| Model requests | ≥1 with `state.cost_source == "tier_map"`, ≥2 candidates, and non-null `state.role_default.model` |
| Per spawn | answer, confidence, `outcome`, `model_source`, `role_default_source`, `tier` and `result.model`, paired with `observed_model` |

**Pass AC-19**
- ≥1 model question.
- ≥1 spawn with `jev_tier` → `openai/…`, or `model_source: role_default`.
- Observed model = `result.model` for those spawns.
- No installed-role spawn ends with `model_source: none` unless it was pinned.

**Also check**
- AC-1: 0 hits.
- `telegram_fired` is reported.

**No Codex re-run is required.** One optional Codex re-run is allowed if the ledger is ≤$3.72 after OpenCode.

## 6. Risks

| ID | Risk | Mitigation |
|:---|:---|:---|
| R1 | OpenAI oauth rejects 6.1-sol or astra overrides. | The plugin's availability cooldown (401/402/403/429) removes the model; record it. |
| R2 | A JEV frontier pick raises quota use. | Frontier is never a role default; it needs 0.9 confidence. |
| R3 | `explore`/`general` are not the OpenCode 2.0.29 agent ids. | Unmatched entries have no effect; QA checks the spawn `agent` values. |
| R4 | `hook.py` or `jev_hooks.rs` goes over its line budget. | Mandated moves; `wc -l` gate. |
| R5 | A user profile has stale explicit ids. | I5: the role tier replaces a default that is not in the catalog. |
| R7 | The QR-D12 skip removes confident Codex tier routing. | Today 0/4; reversible; visible reason code. |
| R8 | A harness run happens while `blackbox_jev.py` is being edited. | One-line change; the run lock. |
| R9 | One paid run; LLM answers vary. | One re-run within the ceiling; the unit tests carry the deterministic proof. |

## 7. Follow-ups (not in scope)

- **F1 (P2):** `anthropic` and `github-copilot` tier-map entries, plus the Copilot profile `gpt-6-terra`, once each catalog is verified.
- **F2 (P2):** split the `hook.py` adapters (D3).
- **F3 (P3):** QR-D7, harness counting after a follow-up turn.
