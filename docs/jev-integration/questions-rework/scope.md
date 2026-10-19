# JEV-QR — JEV questions rework: scope

## Problem statement

A real run ("разработай калькулятор", Claude, software.backend + software.general) sent 11 questions to JEV. Only 2 answers were applied; 9 fell back on `low_confidence`. The questions caused most of it:

- the instructions contained the test case ("calculator", "CRUD");
- the model question used the session model (`opus`) as `default_model`;
- models had no tier and no relative cost;
- workflow options had only `description`;
- permission state carried whole file bodies but no requesting role.

Detailed plan: `/home/e.isaev/.claude/plans/sharded-beaming-pretzel.md` (approved 2026-10-18).

## Decisions (customer-confirmed, 2026-10-18)

- Model options are tiers: `fast | balanced | frontier | clarify`. Tier-to-model mapping is deterministic per host.
- Workflows get a new frontmatter field `selection` (`general`, `use-when`, optional `avoid-when`).
- Confidence thresholds are configurable per question type; the default stays `0.9`.
- In scope: permission question, observability, R&D eval families, paid blackbox runs on **codex, opencode and claude**.
- Branch: `feature/JEV-questions-rework`. Version stays `1.4.0` (unreleased section of `CHANGELOG.md`).

## Acceptance criteria

| ID | Criterion (testable) |
|:---|:---|
| AC-1 | No string sent to JEV or injected as host context contains `calculator` or `CRUD` (case-insensitive). A unit test greps `hook.py` and `questions.py`. |
| AC-2 | Workflow options are built only from `.agent/workflows/*.md` with `type: workflow`. Each option includes description, inputs → outputs, roles and `selection.use-when`; the `general: true` workflow is prefixed `GENERAL.`. Options `native` and `clarify` are always present. |
| AC-3 | A workflow answer `native` gives `fallback/native_request`; `clarify` gives `fallback/clarification_needed`; both keep native host behaviour. An explicit `/trigger` or id match still bypasses JEV. |
| AC-4 | Workflow state contains `original_request`, `installed_areas` and a bounded `repository` snapshot; it does not contain the workflow catalog. The snapshot finishes within its bounds (≤5000 entries, depth ≤6) and does not follow symlinks. |
| AC-5 | Model question options are the available tiers plus `clarify`. State contains `role`, `role_description`, `role_default {model, tier}`, `assignment` (truncated at 2500 chars with `assignment_truncated`), `workflow {id, roles}`, `candidates [{tier, model, relative_cost}]`, `cost_source`, `quota: unknown`. It does not contain the session `default_model`. |
| AC-6 | A confident tier answer is mapped through `model-defaults.json` `tiers` (Claude: fast→haiku, balanced→sonnet, frontier→opus). `clarify`, low confidence or an API error routes to the role default on codex, opencode and claude, with `model_source: role_default`, if that model is a candidate. |
| AC-7 | `model-defaults.json` is written as `{"version": 2, "roles": {...}, "tiers": {...}}` for Claude and Codex. The hook still reads the legacy flat format. OpenCode tiers are derived from candidate prices; unknown prices give no tier routing (role default). |
| AC-8 | Permission state contains no file content and no full command text: only targets (`path`, `in_project`, `new_file`, `bytes`, `kind`), command metadata (`program`, `length`, `args`, `shell_operators`), `agent` (only an installed role, otherwise `null` + `native_agent_type`), `workflow`, `approved_decisions` (≤10). `permission_boundaries` behaviour is unchanged; a confident `allow` with `auto_allow_eligible: false` still becomes `ask`. |
| AC-9 | `settings.jev.thresholds.{workflow,model,permission}` are honoured when in [0.5, 1]; invalid values fall back to 0.9. Reinstall keeps `thresholds`, `lightweight_model` and `tiers` in `.agentic.json`. |
| AC-10 | Every decision record contains `decision`, `threshold`, `applied`, `outcome`, and for spawns `tier` and `model_source`. Observation records for subagent types that are not installed role agents have `agent: null`. Existing `status`/`model` fields keep their meaning (blackbox script compatibility). |
| AC-11 | JEV requests are serialized with `ensure_ascii=False`; a synthetic catalog of 80 workflows with a Cyrillic prompt stays under the 32 KiB request limit. |
| AC-12 | Every `areas/**/workflows/*.md` has a valid `selection` block; `scripts/lint_prompts.py` fails on a missing or invalid block; the template and contributor docs describe it. |
| AC-13 | R&D fixtures `workflow_routing` (12 cases, RU/EN) and `model_tier` (8 cases) are built with the runtime builders from `questions.py` and pass `api.validate`; `make jev-rnd-verify` passes. |
| AC-14 | `make lint` and `make test` pass. |
| AC-15 | Paid blackbox runs for codex, opencode and claude are executed (JEV budget ≤ $5 total). Per host, `docs/jev-integration/verification.md` records: questions asked, answers applied vs. fallback, `model_source`, reason codes, observed subagent models. A host blocked by a manual step (e.g. Codex `/hooks` trust) is recorded as blocked with the reason. |
| AC-16 | `docs/jev-integration/README.md`, `example-request.json`, a `docs/guidance-updates/` note, contributor docs and the `CHANGELOG.md` v1.4.0 section describe the new behaviour. |

## Scope change 1 (PO, 2026-10-19, after first verification)

**What changed**
- AC-8 is amended. When `auto_allow_eligible` is false, the hook does not call JEV at all. The host decides natively, and the record shows `outcome: native` with `reason_code: not_auto_allow_eligible`.

**Why**
- QR-D4 from the Claude blackbox run. For three ineligible Bash commands, JEV leaned to `deny` (deny 0.47–0.52, ask 0.45–0.47) using metadata alone. Above the threshold, this would block legitimate development commands.
- With metadata only, JEV cannot judge hostility.
- When `allow` is impossible, the call adds cost but no value.

**Also in this iteration**
- team-lead P2 findings:
  - snapshot deadline checked during iteration;
  - symlinked or out-of-project targets: no outside size or path; `secret_like` kind when the resolved path is sensitive;
  - guarded `api` import → `runtime_incomplete`;
  - `runtime_incomplete` record written by the Codex and Claude adapters;
  - request preserved in the record when answer mapping fails.
- QR-D3: `api.redact` token patterns get word boundaries, so ordinary words are no longer corrupted.
- R&D `questions` suite uses the same client (`api.py`) and the same configured endpoint and key as the hook.

**Impact**
- No new AC.
- AC-8, AC-10 and AC-13 tests are extended.
- The blackbox runs are repeated for OpenCode and Claude, and for Codex after the user trusts the hooks.

**Deferred (follow-up, owner: team-lead)**
- QR-D2: a default OpenCode install has no role models (`opencode-profile-defaults.json` is `{}`), so no model routing happens. This existed before the change.
- D6: on Codex, the qa default `gpt-6-terra` is not a candidate.

## Scope change 2 (PO, 2026-10-19, customer request)

**What changed**
- QR-D2 moves from deferred into this branch, on one condition: QA confirms that the OpenCode catalog has no usable prices for the candidate models.
- If prices are present, QR-D2 stays deferred and only the missing role models are tracked.

**Why**
- The customer asked what the OpenCode verification really covers.
- Every OpenCode spawn ended as `no_tier_routing`, so model routing on OpenCode was never exercised.
- Without prices, the AC-7 price-derived tiers can never route on OpenCode, even when roles have models.

**Acceptance criteria (added if the condition holds)**

| ID | Criterion (testable) |
|:---|:---|
| AC-17 | A default OpenCode install resolves a default model for every installed role (hook-side, `notes-iteration4.md` I1/I4): the spawn request `state.role_default.model` and the fallback `result.model` are non-null, and the model question has ≥2 candidates. The raw plugin `role_default` may stay `null`. |
| AC-18 | When candidate prices are missing or equal (OpenAI oauth gives `cost: []`, QR-D10), OpenCode tiers come from a shipped deterministic tier map, filtered to models in the host catalog. The record shows `cost_source: "tier_map"`. Runtime prices are still used when they are present (`catalog_price`). Unit tests cover: no prices, partial prices, equal prices, a tier-map model missing from the catalog. |
| AC-19 | A paid OpenCode blackbox run shows at least one model question sent, a tier mapped to a concrete model or a `role_default` fallback with `model_source: role_default`, and the observed subagent models. Results go in `verification.md`. |

| AC-20 | The shipped OpenCode `openai` profile uses only ids that exist in the catalog, with the `openai/` prefix: no bare `gpt-6.1-sol` and no `gpt-6-terra` (QR-D11). The Codex qa role default is a Codex catalog model (D6). A content test checks this. |

**AC-6 amendment (PO, 2026-10-19, QR-D12):** "clarify, low confidence, an API error **or an unavailable (encrypted) assignment** → role default". On Codex a spawn with `assignment_unavailable: true` is not sent to JEV (`fallback/assignment_unavailable`). Evidence: 4/4 `clarify` at 0.40–0.60, so the call cannot change the outcome.

**Also in iteration 4:** QR-D9 (absolute `--run-dir` in `scripts/blackbox_jev.py`). Design: `notes-iteration4.md`.

**Condition check (QA, 2026-10-19):** confirmed. OpenCode on OpenAI oauth passes `cost: []` to the plugin, and every step shows `"cost": 0`. Run `.agentic-blackbox/20261019-114054`. QR-D2 is therefore fixed in this branch, together with QR-D10 and QR-D11. D6 is included because it is the same defect class: a role default that is not a candidate made qa inherit the frontier session model on Codex.

**Impact**
- Adds one design → implementation → QA iteration.
- Adds one OpenCode run (within the $5 JEV budget).
- `delivery_report.md` acceptance is reopened until AC-17–AC-19 pass.

## Non-goals

- No change to `permission_boundaries` auto-allow rules.
- No change to the remote JEV API or the `jev-1.13.0` model.
- No new questions beyond workflow / model / permission.
- No version bump; no release, tag or merge to `main`.
- No changes in `/home/e.isaev/test2` beyond reinstall for manual verification.
