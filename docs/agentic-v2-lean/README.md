# agentic v2 "lean"

Status: v2.0.0 candidate, not shippable yet (see results.md). Scope: root layer (`AGENTS.md`, `MEMORY.md`, `REVIEW_PIPELINE.md`), `software/general`,
`software/backend`, installer profiles, and the quality gate. JEV is frozen: unchanged, and off in every
measurement.

## Why

The 2026-10-20 pilot showed that plain agents beat the v1 pack on every host. The same result came back
in the v2 baseline below. Two causes:

- About 9–12k tokens of always-on text, mostly rules that loaded for every task and every subagent.
- Required orchestration: a mandatory exploration subagent, one subagent per SDLC role, and a Codex
  "always use a subagent" override. Each subagent loads the base context again.

External evidence points the same way. The ICLR 2026 AGENTS.md study (arXiv 2602.11988) found that context
files lower task success and raise cost by more than 20%. Anthropic's guidance is to delete a rule the model
already follows, or to turn it into a hook. v2 therefore keeps the text small and moves quality into
deterministic checks.

## User-facing behavior

| Area | v1.6 | v2.0 |
|---|---|---|
| Root `AGENTS.md` | ~6.5 KB: practices, mandatory exploration | ~3 KB core: load on demand, scale by task size, definition of done, git |
| Rules | All always-on | Path-scoped (`trigger: glob` + `paths:`) or `trigger: manual`. `.claude/rules/` gets only always-on and scoped rules |
| Subagents | 9 SDLC roles; main session is `product-owner` | `lean` profile (default): `explorer` and `reviewer`. Native main session |
| Workflows | Spawn one subagent per role | `lean`: the main session performs role steps. `team`: v1 delegation |
| Quality gate | Prose only | Stop hook runs `make test`/`make lint` when files changed and asks once for a CHANGELOG entry. PreToolUse guard denies secrets, force push, and `rm -rf` outside the project |
| Codex skills | `.agent/skills` (Codex does not read it) | `.agents/skills` |
| Installed workflows | Include the mermaid diagram | Diagram removed (still in the source and docs site) |

### Profiles

- `agentic install --profile lean` (default): two helper subagents and the native main session.
- `agentic install --profile team`: the v1 role team, `product-owner` as main session, Codex override. JEV
  always uses `team`, because it routes between team roles.
- The profile is saved in `.agentic.json` (`settings.profile`) and replayed by `agentic upgrade`.

### Quality gate

- Runtime: `.agent/gate/gate.py`, standard library only. Claude Code and Codex call it from native
  `Stop` and `PreToolUse` hooks. OpenCode calls it from `.opencode/plugins/agentic-gate.ts`.
- Stop: no changed files → no checks. Changed files → run the commands from `.agent/gate.json`
  (`{"commands": [...], "changelog": true, "max_blocks": 3}`), or by default `make test` and `make lint` when
  those targets exist. A failure returns `{"decision": "block", "reason": <command + last 40 lines>}`, so the
  agent continues with the output. Source changes without a new CHANGELOG line are asked about once per
  session. After `max_blocks` consecutive blocks, the gate lets the agent stop and report.
- Guard: denies `.env*` (except `.example`, `.sample`, `.template`), private keys, `git push -f/--force`,
  and recursive deletes outside the project and the system temp directory.
- Evidence: `.agentic/gate/last.json` (changed files, commands, exit codes, output tails).
- `--disable-gate` removes the managed hook groups and the runtime. `--enable-gate` restores them.

## Acceptance criteria

Arms: A0 = plain host, A1 = v1.6 (JEV off, built from `b92d7ef` by `make bench-v1`), A2 = v2 lean.
1 run × 3 hosts × 4 tasks (`tests/bench/tasks.json`); T5 runs on A0 and A2 only. With one run per cell, pass rate is only a guard.
Tokens and deterministic signals are the main criteria.

| # | Metric | Target | Source |
|---|---|---|---|
| K1 | Always-on context per host | ≤ 4k tokens | `make context-budget` |
| K2 | Median uncached tokens (also reported as full input), Claude and Codex | A2 ≤ 0.6 × A1 and ≤ 1.3 × A0 | bench |
| K3 | Accepted tasks per host | A2 ≥ A0 | graders |
| K4 | Question task T3 | 0 subagents, 0 changed files, ≤ 1.2 × A0 tokens | bench |
| K5 | Checks green at the end (T1, T2, T4, T5) | 100% in A2 | grader `delivered_green` |
| K9 | Red-lint trap T5 | A2 accepted; report A0/A2 `delivered_green` | grader |
| K6 | CHANGELOG entry in the feature task T2 | yes on every host | grader |
| K7 | Scope trap T4: files outside the allowlist | 0 | grader |
| K8 | OpenCode | A2 accepted ≥ A0, tokens ≤ A1 | bench |

Ship rule: K1, K3, K4, and K7 are mandatory; K2 applies to Claude and Codex.

## Benchmark

- Fixture: `tests/bench/fixture` (stdlib Python, `make test`, `make lint`). Hidden tests go in only after
  the agent finishes. Reference solutions in `tests/bench/reference` check the graders (`make bench-selftest`).
- Tasks: T1 bugfix (rounding), T2 feature with acceptance criteria and CHANGELOG, T3 question (no changes),
  T4 bugfix next to tempting cleanup (`legacy_report.py` and `_old_level_dump` must stay), T5 bugfix in a file
  that already fails `make lint` (the suite is green, so only an agent or gate that runs lint sees it).
- Seeds: a task with `seed` in `tasks.json` copies `tests/bench/<seed>` over the fixture before the first
  commit. T5 uses it, so T1–T4 keep a lint-clean fixture.
- Allowlists include the version file and `docs/`, because the pack's own completion contract requires them.
  The first baseline grading rejected two v1 cells only for a version bump. `make bench-regrade` applied the
  final allowlists to every cell.
- Commands: `make bench-v1`, `make bench-prepare`, `make bench BENCH_ARGS="--modes lean"` (paid),
  `make bench-regrade`, `make bench-report`. Results: `.agentic-blackbox/bench/` (Git-ignored).
- Tokens: `Input` = uncached + cached. Uncached alone follows prompt-cache hits between runs: Codex lean T3 was
  12.2k vs 7.5k uncached, but 56.0k vs 56.9k input. Claude runs use `--strict-mcp-config`, because an
  account MCP connector attached to one arm only.
- Codex runs project hooks only after `/hooks` trust per absolute path. Trust the
  `/tmp/agentic-bench/codex-T*-lean` projects after `make bench-prepare BENCH_ARGS="--hosts codex --modes lean"`.

## Results

### K1 (offline, `software.backend,software.general`)

| Host | v1.6 | v2 lean | Change |
|---|---|---|---|
| Claude | 12,153 | 1,936 | −84% |
| Codex | 9,420 | 1,495 | −84% |
| OpenCode | 10,808 | 1,766 | −84% |

Estimate: UTF-8 bytes / 4 over instruction files and imports, unscoped rules, the main agent prompt, and
skill, agent, and command descriptions.

### Baseline (2026-10-21, Claude `sonnet`, Codex `gpt-6.1-sol`, OpenCode `openai/gpt-6-luna`)

| Host | A0 plain: accepted · median uncached · median cost | A1 v1.6: accepted · median uncached · median cost |
|---|---|---|
| Claude | 4/4 · 13.4k · $0.070 | 4/4 · 31.7k · $0.185 |
| Codex | 4/4 · 9.4k | 1/4 · 87.1k (3 token caps, 2–3 subagents) |
| OpenCode | 4/4 · 8.0k | 4/4 · 14.6k |

The lean results and the K1–K8 verdict are in [results.md](results.md).

## Limitations

- One run per cell: pass-rate differences under one task are noise (arXiv 2602.07150).
- The fixture is small, and its prompts state the expected outcome. Plain agents pass all tasks, so the
  benchmark shows cost and guards against regressions. It does not show quality gains on hard tasks.
- The OpenCode gate continues a session through `session.prompt`. The one-shot `opencode run` client can
  exit before that follow-up turn. The guard uses permission evaluation and has no live proof yet.
- The `verified_after_edit` trace signal sees only the top-level session, and OpenCode tool events are
  only partly parsed. K5 uses the end state (`delivered_green`) instead.
- Gemini and Antigravity installs get no role agents in `lean`. Use `--profile team` there.
