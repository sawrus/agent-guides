# JEV-QR — Delivery report

**Acceptance decision (product-owner, 2026-10-19, final): APPROVED.**
- AC-1–AC-16 pass on the evidence in `test_report.md`.
- AC-15 Codex was unblocked after the customer trusted the hooks. Run `20261019-003813`: QA GO.
- Scope change 2 (QR-D2 fix) added AC-17–AC-20 and amended AC-6. All of them pass in iteration 4/4a. Evidence: offline probes 82/82 and paid OpenCode run `20261019-121927`.

**Sign-offs**
- QA: GO for iteration 3, for the Codex run, and for iteration 4/4a.
- team-lead: technical GO for iteration 3, and GO for iteration 4. The iteration 4 GO was conditional on fixing P2-1; that fix was made in 4a with a failing-without-fix test.

**Branch state:** `feature/JEV-questions-rework`, not committed, not merged.

## What shipped

**Questions**
- Workflow, model and permission questions no longer contain test-case wording (no "calculator", no "CRUD").
- Workflow options carry purpose, inputs → outputs, roles and `selection.use-when`, plus `native` and `clarify`.
- Workflow state includes the installed areas and a bounded repository snapshot.

**Model routing**
- Model options are tiers: `fast`, `balanced`, `frontier`, `clarify`.
- Tiers map to concrete models through `model-defaults.json` v2.
- On any spawn fallback, all hosts use the role's default model. The session model is never inherited.

**Permissions**
- Permission state carries metadata only, plus the requesting role.
- Requests that cannot be auto-allowed are not sent to JEV (scope change 1).

**Configuration and records**
- Confidence thresholds can be set per question type. They are kept on reinstall.
- New record fields: `decision`, `threshold`, `applied`, `outcome`, `tier`, `model_source`.
- Agent labels follow one rule in every record type.
- Identity hash is v2. Requests are serialized UTF-8 (`ensure_ascii=False`).

**Runtime modules**
- `questions.py`, `routing.py`, `adapters.py`. The runtime is guarded: if a module is missing or outdated, the hook returns `runtime_incomplete`.

**Redaction**
- No more false positives on ordinary words.
- New patterns: GitHub tokens, AWS access key IDs, Slack tokens.

**Content and tooling**
- `selection` block in all 73 workflows, enforced by lint.
- R&D families `workflow_routing` and `model_tier`, run through the hook's client and endpoint.
- Docs updated, `CHANGELOG.md` v1.4.0.

**Iteration 4 (Scope change 2)**
- OpenCode tier map: `extensions/opencode/model-tiers.json`. It is used when runtime prices are missing (OpenAI OAuth gives `cost: []`).
- Every role gets a default model by tier.
- Preferred-provider rule: tiers are never taken from a provider the user did not choose.
- The `openai` profile now uses catalog ids only.
- Codex qa default is `gpt-6.1-sol` (D6).
- Customer change 2026-10-19: qa → `fast` tier in every model-tiers file; Codex qa default is now `gpt-6-luna`.
- Codex spawns with an encrypted assignment skip JEV and use the role default (QR-D12, AC-6 amended).
- The blackbox `--run-dir` is resolved to an absolute path (QR-D9).

## Evidence

| Check | Result |
|:---|:---|
| `make lint` / `make test` | pass: Rust 158/38/13, content 20, jev hooks 86, notify 11 |
| R&D (paid) | workflow_routing 12/12, model_tier 8/8, both option orders |
| Claude blackbox | 10/10 checks. developer → sonnet (JEV, 0.97), Explore → haiku (1.0). 28 permission requests that could not be auto-allowed were decided natively. |
| OpenCode blackbox | workflow applied at 1.0. Model routing unavailable (QR-D2, existed before this change). |
| Codex blackbox | `20261019-003813`: workflow applied at 0.99; 4 spawns fell back to the role default `gpt-6.1-sol`; qa inherited `gpt-6-astra` (D6, now fixed) |
| OpenCode blackbox after the QR-D2 fix | `20261019-121927`: 10 model questions, `tier_map` with `prices: []`. 3 answers routed by JEV (explore fast ×2, developer balanced) and 7 role defaults. 10/10 observed models = routed models. `model_applied_to_subagent` true for the first time on OpenCode |
| Iteration 4 gates | `make lint`, `make test` (Rust 161/38/13, content 25, jev 105, notify 31), `make jev-rnd-verify`: rc 0 |
| JEV budget ledger | $1.94 → $3.56 of $5 |

Baseline: 2 of 11 decisions applied, and developer inherited opus. After the change on Claude, the developer got sonnet. Spawns that fell back used the role default (team-lead → opus, qa → sonnet).

## Deferred / open items

| ID | Item | Severity | Owner |
|:---|:---|:---|:---|
| QR-D13 | The OpenCode hook spends a JEV call on a `product-owner` spawn that OpenCode rejects (`mode: primary`) | P3 | team-lead |
| F1 | Add `anthropic` and `github-copilot` tier-map entries, and fix the Copilot profile `gpt-6-terra`, once those catalogs are verified | P2 | team-lead |
| R1 | OAuth acceptance of `openai/gpt-6-astra` is not yet seen at runtime | P3 | QA |
| QR-D12 | The Codex skip is verified offline only | P3 | QA |
| Iteration 4 P3s | Frozen catalogs reflect listings, not OAuth usability. The price path does not enforce a single provider. `test_hooks.py` is 474 lines | P3 | team-lead |
| QR-D7 | The blackbox verifier ignores records after the approval follow-up, so evidence is under-counted | P3 | team-lead |
| TL-P2 | `sk-`-prefixed hyphenated words of 20+ characters are over-redacted (fails safe) | P2 | developer |
| TL-P2 | `hook.py` is 490 lines and `questions.py` 398, close to the limits | P2 | team-lead |

## Residual risks

- Model confidence is often below 0.9 (OpenCode: 3 of 10; Codex: 0 of 4, now skipped), so their role defaults decide. Tune thresholds from production records.
- Each host ran once; LLM behaviour varies between runs.

## Rollout and rollback

- **Rollout:** rebuild `agentic` and reinstall in a target project. The installer writes `questions.py`, `routing.py`, `adapters.py` and `model-defaults.json` v2.
- **OpenCode:** restart OpenCode after a reinstall; the plugin reads the tier map once, at setup.
- **Compatibility:** the old flat `model-defaults.json` is still read.
- **Rollback:**
  - Reinstall from `main` (v1 runtime).
  - Or disable JEV with `--disable-jev` / `AGENTIC_ENABLE_JEV=0`; the hosts then run natively.
- **Old records:** identity v2 means records cached by the old runtime are not reused.

## Lessons learned

- Wording from a test case placed in production instructions hides real model quality. Keep held-out cases in R&D.
- Fallbacks need a safe direction. Inheriting the session model meant opus.
- Metadata-only permission state needs an explicit "skip when allow is impossible" rule. Otherwise the model drifts toward `deny`.
