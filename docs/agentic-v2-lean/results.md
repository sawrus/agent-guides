# agentic v2 lean: benchmark results (2026-10-21 to 2026-10-27)

Protocol: [README.md](README.md). Total: 36 paid cells, 1 run each (A0 plain, A1 v1.6 with JEV off, A2 v2 lean,
× 3 hosts × 4 tasks). Models: Claude `sonnet`, Codex `gpt-6.1-sol`, OpenCode `openai/gpt-6-luna`. Every cell
was graded again with the final `tasks.json` (`make bench-regrade`). Codex lean ran with the gate hooks trusted.

## Round 6: rules H0, H4, H-clean, H-clean-devops (2026-10-27)

Rules: [README.md](README.md#round-6-decision-rules-fixed-before-the-run), fixed before the run. Models: Claude
`sonnet`; Codex `gpt-6.1-terra` (codex-cli 0.164; 0.153.2 returns `model_not_found` for this model on a ChatGPT
account). Cells: `.agentic-blackbox/bench-r6`, `bench-r6-t8v2`, `bench-r6-devops` (before the content cleanup)
and `bench-r6-clean`, `bench-r6-devops-clean` (after it), Git-ignored. Codex cost is an API-equivalent estimate;
the `gpt-6.1-terra` price in `tests/bench/prices.json` is an estimate equal to `gpt-5.6-terra`. Full tokens =
uncached + cached input. One Claude cell (T6 `lean-jev` r3) is `harness_error` (`git status` exit 128 in the cell
directory) and is not counted.

| Rule | Host | Measured | Verdict |
|---|---|---|---|
| H4: reviewer in the lean default | Codex T8v2 | `lean` 9/9 vs `lean-noreviewer` 9/9; median full 134.6k vs 108.1k; cost per success $0.083 vs $0.081 | not met (needs +2 accepted) |
| | Claude T8v2 | 3/3 vs 3/3; median full 109.0k vs 138.2k; cost per success $0.098 vs $0.114 | guard holds |
| H0: no lean helper above the session tier | Codex T6–T8 | `lean` 9/9, `lean-jev` 9/9; 6 helper spawns (T7, 3 per arm), all on `gpt-6.1-terra`, none on a frontier model; cost per success $0.096 vs $0.088 (× 1.09) | met |
| | Claude T6–T8 | `lean` 9/9, `lean-jev` 8/8 valid; 0 helper spawns | inconclusive |
| H-clean: cleanup on the core selection, T1–T7 + T10, r1 | Claude | accepted 8/8 before and after; full 1,211k → 1,122k (× 0.93); uncached 128k → 135k (× 1.05); cost $0.755 → $0.770 (× 1.02) | quality kept; full ≤ 0.9 × not met |
| H-clean-devops: cleanup on T11, 3 reps | Claude `lean` | accepted 3/3 before and after; full 458k → 441k (× 0.96); uncached 83k → 60k (× 0.72); cost $0.434 → $0.369 (× 0.85) | quality kept; full ≤ 0.9 × not met |
| | Claude `plain` (noise control) | accepted 0/3 before and after; full 444k → 366k (× 0.83); cost $0.253 → $0.229 | — |

What the cells show:
- No T8v2 cell started a subagent on either host, so the reviewer never ran on the task built to need it. Lean
  without the reviewer accepted every T8v2 cell, including the hidden `release_many` defect. Decision: the
  `reviewer` helper leaves the lean default (lean installs only `explorer`); a custom profile can still add it.
- Codex T7 (multi-module feature) started one `reviewer` helper per cell in both `lean` and `lean-jev`; these are
  the 6 helper spawns of H0. JEV recorded the spawn as `reviewer` and observed `gpt-6.1-terra`, the session model.
  The tier cap from round 4 (tech debt item 21) holds: Codex lean + JEV is at × 1.09 of lean, down from × 1.43.
- Every plain T11 cell fails `hidden_check` on the Kubernetes rule items (`readOnlyRootFilesystem`,
  `capabilities.drop`, `seccompProfile`, a dedicated ServiceAccount). Every lean T11 cell meets them. The rules
  carry the result on this task, before and after the cleanup.
- The cleanup cuts the always-on context, but the full-token sum is dominated by the cached session history, so
  the 0.9 × threshold on full tokens is not met on either selection. On the devops selection the uncached tokens
  (× 0.72) and the cost (× 0.85) fall clearly; on the core selection they stay within noise.
- The T10 grader was fixed before the run: `make dev` became a conditional item, so every rule version can pass.
- Codex H-clean cells were not run; H-clean has Claude evidence only.

**Decisions.** H4 applied: `reviewer` leaves the lean default. H0 met on Codex, inconclusive on Claude. H-clean
partly met: quality kept on both selections and cost down on the devops selection, but the full-token threshold is
not met. Future rounds use cost and uncached tokens as the primary token metric (see README).

## Round 4: Lean + JEV, 3 repetitions (2026-10-23 and 2026-10-24)

252 paid cells: 4 arms × 3 hosts × T1–T7 × 3 repetitions, seeded random order, every cell valid (0
`harness_error`). Claude cells are in `.agentic-blackbox/bench-r4`; Codex and OpenCode cells, and the joined
report, are in `.agentic-blackbox/bench-r5` (Git-ignored). Models: Claude `sonnet`; Codex `gpt-5.6-terra` (the
ChatGPT account rejects `gpt-6.1-sol` and `gpt-6-sol`); OpenCode `private_llm/coding-agent-default`, which is
Qwen3.8-Flash-Next on a private LiteLLM. Codex and OpenCode numbers do not compare with rounds 1–3, which used
other models.

Per host and arm, n = 21. Full tokens = uncached + cached input, median. Cost per success = total cost / accepted
cells. Claude cost is `total_cost_usd`; Codex and OpenCode cost is an API-equivalent estimate from
`tests/bench/prices.json`.

| Host | Arm | Accepted (95% CI) | Full tokens | Subagents (mean) | Cost per success | Lean + JEV ÷ lean |
|---|---|---|---|---|---|---|
| Claude | plain | 18/21, 86% (65–95%) | 93.7k | 0 | $0.092 | |
| Claude | lean | 21/21, 100% (85–100%) | 156.2k | 0 | $0.095 | |
| Claude | lean + JEV | 21/21, 100% (85–100%) | 130.5k | 0 | $0.097 | 1.02 |
| Claude | team + JEV | 21/21, 100% (85–100%) | 132.1k | 0 | $0.073 | |
| Codex | plain | 18/21, 86% (65–95%) | 81.3k | 0 | $0.059 | |
| Codex | lean | 21/21, 100% (85–100%) | 126.7k | 0.14 | $0.072 | |
| Codex | lean + JEV | 21/21, 100% (85–100%) | 119.9k | 0.14 | $0.103 | 1.43 |
| Codex | team + JEV | 18/21, 86% (65–95%) | 165.1k | 0.62 | $0.301 | |
| OpenCode | plain | 19/21, 90% (71–97%) | 123.3k | 0 | $0.026 | |
| OpenCode | lean | 19/21, 90% (71–97%) | 159.8k | 0.19 | $0.041 | |
| OpenCode | lean + JEV | 17/21, 81% (60–92%) | 147.1k | 0 | $0.046 | 1.12 |
| OpenCode | team + JEV | 18/21, 86% (65–95%) | 162.8k | 0.95 | $0.047 | |

Accepted per task, all hosts (n = 9):

| Task | plain | lean | lean + JEV | team + JEV |
|---|---|---|---|---|
| T1–T4 | 36/36 | 36/36 | 36/36 | 36/36 |
| T5 (red lint) | 1/9 | 7/9 | 6/9 | 6/9 |
| T6 (multi-module bugfix) | 9/9 | 9/9 | 9/9 | 7/9 |
| T7 (multi-module feature) | 9/9 | 9/9 | 8/9 | 8/9 |

What the cells show:
- Every plain failure is T5 with `make lint` red: 3/3 on Claude, 3/3 on Codex, 2/3 on OpenCode. Lean passes T5 on
  Claude and Codex every time. On OpenCode every arm fails T5 most of the time; its gate cannot continue a
  one-shot `opencode run` (tech debt item 7).
- T6 and T7 did not separate the arms: plain passed both 9 of 9. Item 17 stays open.
- JEV made one prompt decision per session: a workflow in 3 of 21 sessions per arm and host, `native` in the rest
  (15 `low_confidence`, 3 `native_request`). JEV cost $0.0015 per 21 cells.
- Codex lean + JEV costs more than lean at the same success rate because JEV routed 4 helper spawns to
  `gpt-6-astra` (frontier, 5 × the terra price). Codex team + JEV routed 18 spawns to astra and hit the token cap
  twice on T6 (tech debt item 21).
- Claude team + JEV has the lowest cost per success, but its uncached median is 5.3k against 11.3k for plain. Its
  long, identical role-team prefix was already in the 1-hour prompt cache from earlier team + JEV cells (first
  request: 0 cache writes, 23.9k cache reads; plain: 8.5k cache writes). This is a cache-order effect, not a JEV
  saving.
- OpenCode reports no cached tokens for this provider, so its full and uncached tokens are equal. Do not compare
  its dollars with the other hosts.
- 7 OpenCode JEV cells first ran with routed subagents on `openai/*` models, because the harness forced the JEV
  provider to `openai`. They were run again on the Qwen provider only; the first copies are in
  `.agentic-blackbox/bench-r5-mixed` and are not counted.

**Decision under the rule fixed before the round.** Lean + JEV meets the rule on Claude (same success, 1.02 ×
lean). It misses it on Codex (1.43 × lean) and OpenCode (1.12 × lean, 2 fewer accepted cells; the intervals
overlap). It is cost-neutral at best and gives no measured quality gain, so it stays opt-in. Lean stays the
default. No savings are claimed.

Limitations: small fixture; n = 3 per task; API-equivalent prices from secondary sources; Claude cache-write cost
is in `total_cost_usd`, while Codex and OpenCode estimates have no cache-write price; Codex and OpenCode models
differ from Claude's tier, so compare arms only inside one host.

## Round 2: targeted re-run (2026-10-22)

20 paid cells, 1 run each, in `.agentic-blackbox/bench-r2` (Git-ignored): T3 and T5 on A0/A2 × 3 hosts, Codex T2
A0/A2, OpenCode T4 A2. The core now carries the fixes for tech debt items 1–4. Claude ran with
`--strict-mcp-config`. **Codex ran on `gpt-6-astra`**: the ChatGPT account no longer accepts `gpt-6.1-sol`.
Codex numbers therefore compare only inside round 2.

| Task | Host | A0 accepted / uncached / input | A2 accepted / uncached / input | Subagents A2 |
|---|---|---|---|---|
| T2 | Codex | yes / 11.3k / 102.9k | yes / 76.7k / 336.3k | 2 (reviewer) |
| T3 | Claude | yes / 11.6k / 66.1k | yes / 13.9k / 73.3k | 0 |
| T3 | Codex | yes / 3.7k / 44.8k | yes / 12.3k / 55.1k | 0 |
| T3 | OpenCode | yes / 7.6k / 7.6k | yes / 9.9k / 18.7k | 0 |
| T4 | OpenCode | (round 1: yes) | yes / 41.5k / 69.1k | 0 |
| T5 | Claude | **no** (lint red) / 12.6k / 89.7k | yes / 16.6k / 204.6k | 0 |
| T5 | Codex | yes / 11.7k / 94.0k | yes / 23.8k / 103.4k | 0 |
| T5 | OpenCode | **no** (lint red) / 9.6k / 49.0k | yes / 12.1k / 60.5k | 0 |

| # | Result | Status |
|---|---|---|
| K3 | Every A2 cell is accepted. Codex T2, the round 1 failure, is accepted. On T5, A2 beats A0 on Claude and OpenCode. | met |
| K4 | T3: 0 subagents and 0 changed files on every host. Uncached A2 ÷ A0: 1.20 / 3.28 / 1.29; full input: 1.11 / 1.23 / 2.45 (Claude / Codex / OpenCode). | not met (tokens) |

**Decision under the ship rule: still do not ship v2.0.0 as a default.** K3 now passes, K4 still fails on
tokens. Claude sits on the 1.2 line. With one run per cell the ratios are noisy: OpenCode A0 T3 had no
prompt-cache hit at all, and Codex A0 T3 used only 3.7k uncached on the new model.

What the traces show:
- Items 1–2 hold. Codex T2 lean read no rule files and started no explorer. Its 2 subagents are the reviewer
  that the core asks for after a feature diff: `/root/review` failed on `gpt-6.1-sol` with 0 tokens, and Codex
  retried as `/root/review_fallback` on `gpt-6-astra` (24.6k uncached). The installed reviewer pins a model the
  account no longer serves (tech debt item 20).
- Item 4 holds. OpenCode T4 lean changed `CHANGELOG.md`, the fix, and its test; no version file.
- The Codex gate hooks ran without `--no-daemon`: each lean project has a fresh `.agentic/gate/last.json` with
  green `make test` and `make lint`.

## Round 3: Codex lean after the fixes (2026-10-22)

2 paid cells in `.agentic-blackbox/bench-r3`, Codex lean on `gpt-6-astra`, after commits `55e1a22` (memories off,
agent models unpinned) and `350b2b8` (reviewer only for multi-module diffs). A0 is the round 2 plain cell.

| Task | Uncached r2 → r3 | Input r2 → r3 | A0 input | Input ÷ A0 | Subagents r2 → r3 |
|---|---|---|---|---|---|
| T2 | 76.7k → 47.2k | 336.3k → 244.4k | 102.9k | 2.38 | 2 → 1 (reviewer, 20.4k) |
| T3 | 12.3k → 26.4k | 55.1k → 49.7k | 44.8k | 1.11 | 0 → 0 |

- The rollout has no `## Memory` block. Lean context per request fell from 22.7k to 15.4k characters; plain is
  10.2k.
- T3 uncached rose because the changed prompt prefix was not yet in the prompt cache (cached 23.3k vs 42.9k).
  Full input is the stable measure here, and it is within K4's 1.2 × A0.
- T2 still started the reviewer: the diff touched `pricing.py` and `cli.py`, so it spans several modules under the
  new rule. The reviewer no longer fails on a retired model.

## Round 1 (2026-10-21)

## Summary per host

| Host | Accepted A0 / A1 / A2 | Median uncached A0 / A1 / A2 | A2 ÷ A1 | A2 ÷ A0 |
|---|---|---|---|---|
| Claude | 4 / 4 / 4 | 13.4k / 31.7k / 18.1k | 0.57 | 1.35 |
| Codex | 4 / 1 / 3 | 9.4k / 87.1k / 21.5k | 0.25 | 2.29 |
| OpenCode | 4 / 4 / 4 | 8.0k / 14.6k / 18.4k | 1.27 | 2.31 |

Claude total cost for 4 tasks: A0 $0.29, A1 $0.70, A2 $0.43.

## Verdict per criterion

| # | Target | Result | Status |
|---|---|---|---|
| K1 | Always-on ≤ 4k tokens | 1.9k / 1.5k / 1.8k (−84%) | met |
| K2 | A2 ≤ 0.6 × A1 and ≤ 1.3 × A0 (Claude, Codex) | Claude 0.57 / 1.35; Codex 0.25 / 2.29 | half met |
| K3 | A2 accepted ≥ A0 | Claude 4 = 4, OpenCode 4 = 4, Codex 3 < 4 | not met (Codex) |
| K4 | T3: 0 subagents, 0 changes, ≤ 1.2 × A0 | 0 subagents and no changes everywhere; tokens 1.24 / 1.62 / 1.43 × A0 | not met (tokens) |
| K5 | Checks green at the end (T1, T2, T4) | 9 / 9 | met |
| K6 | CHANGELOG entry in T2 | Claude yes, OpenCode yes, Codex no (cell hit the cap) | not met (Codex) |
| K7 | Scope trap T4: 0 files outside the allowlist | 0 on every host | met |
| K8 | OpenCode: accepted ≥ A0, tokens ≤ A1 | 4 = 4; 18.4k > 14.6k | not met (tokens) |

**Decision under the ship rule: do not ship v2.0.0 as a default yet.** The rule requires K3 and K4, and
both fail. v2 is much cheaper than v1 on Claude (−43% tokens, −39% cost) and Codex (−75% tokens, three fewer
token caps). It still costs more than a plain host on every host.

## Root causes seen in the traces

1. **Eager reads of on-demand guidance.** Codex T2 read `general-dev-tools/SKILL.md`, `security.md`,
   `readme-sync-guide.md`, and `git-workflow-guide.md` for a small pure-function change. The rule tables in
   spec `AGENTS.md` invite reads that the task does not need.
2. **Native helper spawn.** Codex T2 started its native `explore` subagent, which used 47.8k uncached
   tokens on a 200-line repository and pushed the cell over the 80k cap. The core allows an explorer "only
   when the code is unfamiliar", and the model judged that it was.
3. **Definition-of-done work.** Lean agents add tests, a CHANGELOG line, and sometimes a version bump on
   bugfixes, which plain agents skip. That is intended SDLC behavior, but it costs about 3–5k tokens per task.
4. **Fixed startup cost.** On T3 (a question) the lean overhead is about 3k tokens on Claude, 4.7k on Codex,
   and 2.8k on OpenCode, above the estimated 1.5–1.9k always-on text. Hook and tool descriptions add to it.

The gate never blocked a run: each agent ran the checks and wrote the CHANGELOG itself. On these easy tasks
the gate is only insurance. The benchmark does not show its value on tasks where agents stop with red checks.

## Next iteration (proposed, not done)

Tracked as items 1–6 in [tech_debt.md](tech_debt.md).

- Remove the rule tables from spec `AGENTS.md`. Claude already has `paths:`. For Codex and OpenCode, link the
  rules from the skills and workflows that need them.
- Core: "Do not start an explorer for a repository you can list in one command", and "Read a rule or skill
  only when the task touches its subject".
- Bugfix definition of done: CHANGELOG only, no version bump. That matches "a completed feature updates the
  version".
- Repeat only the failing cells: Codex T2, all T3, OpenCode T4 (6 paid runs). If K3 and K4 then pass, run
  the full A2 row again.
