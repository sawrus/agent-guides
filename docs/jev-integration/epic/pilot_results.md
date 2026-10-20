# Comparative pilot results (2026-10-20)

Exploratory, single run per cell. Protocol: [pilot.md](pilot.md); frozen criteria: [pilot_acceptance.md](pilot_acceptance.md); raw anonymized cells: [pilot-results.json](pilot-results.json); every measured value: [measurements/](measurements/). Open items: [tech debt](tech_debt.md). Hosts: Codex 0.163.0 (`gpt-6.1-sol` coordinator), Claude Code 2.1.304 (`sonnet`), OpenCode 2.0.29 (`openai/gpt-6-luna`). Tasks: A infra feasibility, B static code review, C console calculator. Caps: 50,000 uncached tokens and six minutes per cell.

## Accepted cells and median uncached tokens

| Mode | Codex | Claude Code | OpenCode | All hosts |
| --- | --- | --- | --- | --- |
| plain (no agentic) | 3/3 · 29.0k | 3/3 · 19.4k | 2/3 · 41.3k | **8/9 · 19.8k** |
| fixed workflow, JEV off | 0/3 · 61.2k | 0/3 · 53.9k | 1/3 · 50.2k | 1/9 · 53.9k |
| agentic + JEV | 1/3 · 54.1k | 1/3 · 40.7k | 1/3 · 50.4k | 3/9 · 49.7k |
| JEV workflow only (A, C) | 0/2 · 50.7k | 1/2 · 48.7k | 1/2 · 32.3k | 2/6 · 46.9k |
| JEV models only (A, C) | 0/2 · 60.1k | 0/2 · 52.7k | 1/2 · 54.5k | 1/6 · 55.7k |

Totals: 39 cells, 15 accepted, 16 stopped by the token cap, 8 rejected. 1.72M uncached and 9.24M cached input tokens. Claude cost $3.86. JEV: 59 calls, 91.5k tokens (counted separately).

## Findings

1. **The agentic playbook dominates cost on small tasks.** Agentic modes start by loading the workflow and role profiles, and every native subagent loads its own base instructions. A fresh Codex subagent costs roughly 20–25k uncached tokens before work starts; a Claude agentic session writes 40–50k tokens to cache on the first turn. Fixed workflows reached the cap in 30–60 seconds.
2. **JEV workflow selection was not confident on A and B.** On all hosts the first prompt for A and B returned `low_confidence`, so the session switched to native mode after the agentic context was already loaded. JEV picked `development-cycle-workflow` for C.
3. **JEV lowered cost compared with the fixed workflow** (median 49.7k against 53.9k, 3/9 against 1/9 accepted), but it did not beat the plain agent in any host.
4. **No savings are claimed.** Single cells per combination are exploratory, and the tasks are deliberately small. The comparison says nothing about larger multi-step work, where process and review are the reason to use agentic.

## Deviations and measurement limits

- **Accounting.** Caps count uncached tokens (user decision, recorded in [pilot.md](pilot.md)).
- **OpenCode live cap.** The live cap saw only the parent session; child sessions were added from `session export` after the run. Two OpenCode cells (A-jev, C-fixed) finished above 50k without a live stop.
- **Shared quota.** OpenCode `openai/*` and Codex draw from the same ChatGPT Plus 5-hour limit.
  - `opencode-C-models_only` first hit that limit inside a subagent. The cell was marked `quota_exhausted` and run once after the reset. The first attempt is kept as invalidated evidence.
  - The runner now stops a host on provider quota errors.
- **Task B criterion.** Task B's frozen check counts distinct `src/...py:<line>` references rather than findings. Claude B-fixed and B-jev had 9–10 findings with more than 10 references and were rejected by the frozen rule. A findings-based rescore would accept them; the frozen result is reported above.
- **Task A criterion.** Task A's check requires three named dashboards. Some substantive reports named two and used `*.json` for the rest.
- **Not done yet.** Human quality review of the anonymized outputs has not been done.

## What this suggests

Reduce always-loaded context first: rules, root `AGENTS.md`, `MEMORY.md`, `REVIEW_PIPELINE.md` and role profiles. Let small tasks stay native. Re-run the same cells after a reduction to measure the effect.
