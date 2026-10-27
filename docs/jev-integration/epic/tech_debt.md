# JEV-EPIC technical debt (open after 2026-10-20)

Each item has a source, an owner role and a done-when condition. Evidence: [pilot results](pilot_results.md), [measurements](measurements/), [native facts](native-smoke.json).

## Product and runtime

| # | Item | Source | Owner | Done when |
| --- | --- | --- | --- | --- |
| 1 | **Always-loaded context is the main cost.** On small tasks the agentic modes used about 2.7× the tokens of a plain agent and hit the 50k cap in 16 of 30 agentic cells. Rules, root `AGENTS.md`, `MEMORY.md`, `REVIEW_PIPELINE.md` and role profiles load at start (≈15k tokens for the pilot selection); every Codex subagent adds ≈20–25k. | pilot findings 1–3 | team-lead | Always-on text is cut by at least 50%; the same 39 cells are re-run with `scripts/pilot_jev.py`; the median uncached tokens and acceptance for the agentic modes are published next to the 2026-10-20 baseline. |
| 2 | **Small tasks should stay native.** JEV workflow selection returned `low_confidence` for tasks A and B on all hosts after the agentic context was already loaded. | pilot finding 2 | product-owner | A bounded or single-file request skips workflow loading (or JEV can answer `native` cheaply before it), verified on the A/B cells. |
| 3 | **OpenCode installer writes `"model": ""` for agents.** OpenCode 2.x logs "unsupported legacy model reference" and drops the field. | debug log, GIF recording | developer | Agents without a model omit the key; an installer test covers it; no normalization warning on OpenCode 2.0.29. |
| 4 | **OpenCode live token cap sees only the parent session.** Child usage is known only after `session export`. A-jev and C-fixed ended above 50k without a live stop. | pilot deviation | developer | The runner polls child sessions during the run and stops the cell at the cap; a synthetic test covers it. |
| 5 | **Codex and OpenCode share one ChatGPT Plus 5-hour limit.** One cell was invalidated by the quota; the runner now stops on quota errors. | provider 429 headers | team-lead | The pilot plan schedules shared-quota hosts in separate windows, and quota before/after is recorded per host from the provider, not by hand. |
| 6 | **Codex per-child usage in `exec --json` is coordinator-only.** Child usage was read from rollout files. | GIF/live runs | developer | The review usage table names this source explicitly or uses a public host counter when one exists. |
| 7 | **Embedded runtime can be stale after an edit.** One rebuild installed an old `adapters.py` until another build. | live check 3 | developer | `build.rs` or the embed step re-runs when `extensions/**` changes; a test compares installed runtime files with the sources. |

## Evaluation

| # | Item | Source | Owner | Done when |
| --- | --- | --- | --- | --- |
| 8 | **Task B criterion counts references, not findings.** Claude B-fixed/B-jev were rejected with 9–10 findings. | pilot deviation | qa | The next pilot freezes a findings-based rule before any run; the 2026-10-20 results keep the old rule and mark the difference. |
| 9 | **Task A criterion is strict on named dashboards.** | pilot deviation | qa | The rubric accepts a justified glob, or the prompt asks for explicit names; frozen before the next run. |
| 10 | **Human quality review of pilot outputs not done.** | pilot protocol | qa + product-owner | Anonymized outputs of all accepted and rejected cells are rated with one rubric and published. |
| 11 | **Single run per cell.** | pilot protocol | team-lead | At least three runs per cell for any claim of savings or quality. |

## Platforms and release

| # | Item | Source | Owner | Done when |
| --- | --- | --- | --- | --- |
| 12 | **Antigravity, Gemini, Cursor, Kilocode have no recorded run.** README marks them "configs only". | README | devops-engineer | Each host runs the GIF prompt and one pilot cell in its own CLI; the badge changes only with that evidence. |
| 13 | **Profile sandbox narrowing is unproven.** Codex children reported the parent's `danger-full-access`, independent of naming, because this host blocks bwrap for `workspace-write`. | live runs | devops-engineer | A host with working bwrap shows whether a `workspace-write` role profile narrows a broader parent. |
| 14 | **Post-task review, merge and release pending.** | handoff | product-owner | The user approves merge; review specialists run once; version tag and release notes are published. |
| 15 | **Draft PR #76 description is stale.** No `gh` on the work host. | handoff | product-owner | The PR body matches the final state (text kept in the local run directory). |

## Measurement inventory

- `measurements/pilot-cells.json`: all 39 cells. Includes status, cap, turns and time; acceptance checks; uncached and cached tokens per agent and model; Claude cost; JEV calls, usage and decisions. No paths, prompts or outputs.
- `measurements/native-checks.json`: Codex live checks (failed and proven), the invalidated quota cell, GIF host runs, OpenCode meter calibration and quota.
- `pilot-results.json`: the compact per-cell table that the scorecard used until v8.1.1 (it now shows benchmark round 6).
- `native-smoke.json`: narrow native checks and earlier smoke runs.
- `../../../reports/area-quality.json`: static guidance quality.
- Raw traces and project copies stay local in the Git-ignored `.agentic-blackbox/pilot-20261020/` and `/tmp/agentic-pilot/`. They contain private target content and are not published.
