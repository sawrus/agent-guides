# plain vs SDLC vs JEV vs lean: all measurements (2026-10-22)

This page joins two measurement sets. Their tasks and caps differ, so compare numbers only inside one table.
Every cell is one run.

Modes:
- **plain**: the host agent without agentic.
- **SDLC without JEV**: the v1 role team (`team`), JEV off. The pilot calls it "fixed workflow"; the benchmark
  calls it A1/`v1`.
- **SDLC + JEV**: the role team, with JEV choosing the workflow and the models.
- **lean**: v2 without JEV. JEV always selects `team` (`profile::is_team`), so lean + JEV was never measured.

## Set 1: JEV pilot (2026-10-20)

Source: [pilot_results.md](../jev-integration/epic/pilot_results.md). Tasks A (infra feasibility), B (static code
review), C (console calculator). Cap: 50k uncached tokens per cell. Format: accepted · median uncached · cells
stopped by the cap.

| Mode | Claude | Codex | OpenCode | All hosts |
|---|---|---|---|---|
| **plain** | **3/3** · 19.4k · $0.33 | **3/3** · 29.0k | **2/3** · 41.3k | **8/9** · 19.8k |
| SDLC without JEV | 0/3 · 53.9k · cap 2 · $0.99 | 0/3 · 61.2k · cap 3 | 1/3 · 50.2k · cap 1 | 1/9 · 53.9k |
| SDLC + JEV | 1/3 · 40.7k · $1.28 | 1/3 · 54.1k · cap 2 | 1/3 · 50.4k · cap 1 | 3/9 · 49.7k |
| JEV workflow only | 1/2 · 48.7k · cap 1 | 0/2 · 50.7k · cap 2 | 1/2 · 32.3k | 2/6 · 46.9k |
| JEV models only | 0/2 · 52.7k · cap 1 | 0/2 · 60.1k · cap 2 | 1/2 · 54.5k · cap 1 | 1/6 · 55.7k |

JEV calls are counted separately: 59 calls, 91.5k tokens.

## Set 2: SDLC benchmark (2026-10-21 and 2026-10-22)

Source: [results.md](results.md). Tasks T1–T4 (bugfix, feature, question, scope trap). Cap: 80k uncached tokens.

| Mode | Claude | Codex | OpenCode |
|---|---|---|---|
| **plain** | 4/4 · 13.4k · $0.29 | 4/4 · 9.4k | 4/4 · 8.0k |
| SDLC without JEV (v1) | 4/4 · 31.7k · $0.70 | **1/4** · 87.1k · cap 3 | 4/4 · 14.6k |
| lean, round 1 | 4/4 · 18.1k · $0.42 | 3/4 · 21.5k · cap 1 | 4/4 · 18.4k |
| lean, latest run per task | 4/4 · 18.1k | 4/4 · 26.0k | 4/4 · 20.4k |

"Latest run per task" takes the newest of rounds 1–3. Codex rounds 2–3 ran on `gpt-6-astra`, round 1 on
`gpt-6.1-sol`, so the Codex row mixes models.

T5, a bugfix in a file where `make lint` is already red (accepted · uncached):

| Mode | Claude | Codex | OpenCode |
|---|---|---|---|
| plain | no (lint red) · 12.6k · $0.067 | yes · 11.7k | no (lint red) · 9.6k |
| lean | yes · 16.6k · $0.103 | yes · 23.8k | yes · 12.1k |

On Claude the Stop gate blocked the finish with red lint, and the agent fixed it. On OpenCode the agent fixed
lint by the core instruction; the gate did not fire.

## Per host

| Host | Best mode | Evidence |
|---|---|---|
| Claude | plain for cost; lean for quality | SDLC + JEV is cheaper than SDLC without JEV (40.7k vs 53.9k) but accepts 1 of 3. Lean is the only mode where the gate caught a defect (T5). Lean costs 1.35 × plain. |
| Codex | plain | SDLC modes mostly hit the cap (0/3, 1/3, 1/4). Lean now accepts every task, but plain does too at a half to a third of the tokens. No measured quality gain. |
| OpenCode | plain for cost; lean for quality | SDLC and JEV modes accept 1 of 2–3. Lean accepts all tasks and catches T5, but costs 2.3–2.6 × plain and more than v1. |

## Conclusions

1. **plain accepts as many tasks as any mode, or more, everywhere except T5**, and it is the cheapest on every
   host.
2. **SDLC without JEV is the weakest mode:** 1 of 9 accepted in the pilot, and 3 cap stops in 4 Codex tasks in the
   benchmark.
3. **JEV improves the SDLC team but does not reach plain:** 3/9 accepted against 1/9 without JEV and 8/9 for
   plain. Most of the cost is the role-team context, not JEV itself.
4. **lean nearly matches plain on accepted tasks and beats it on T5.** It costs 1.35–2.8 × plain, and 1.7–4 × less
   than v1.
5. **Not measured:** lean + JEV, and large multi-step tasks where the process should pay off. Both task sets are
   small. One run per cell cannot separate a one-task difference from noise (tech debt items 13 and 17).
