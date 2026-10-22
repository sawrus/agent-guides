# agentic v2 lean: benchmark results (2026-10-21)

Protocol: [README.md](README.md). Total: 36 paid cells, 1 run each (A0 plain, A1 v1.6 with JEV off, A2 v2 lean,
× 3 hosts × 4 tasks). Models: Claude `sonnet`, Codex `gpt-6.1-sol`, OpenCode `openai/gpt-6-luna`. Every cell
was graded again with the final `tasks.json` (`make bench-regrade`). Codex lean ran with the gate hooks trusted.

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
