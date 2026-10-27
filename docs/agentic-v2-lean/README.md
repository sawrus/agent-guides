# agentic v2 "lean"

Status: v2.0.0 candidate, not shippable yet (see results.md). Scope: root layer (`AGENTS.md`, `MEMORY.md`, `REVIEW_PIPELINE.md`), `software/general`,
`software/backend`, installer profiles, and the quality gate. JEV was off in the measurements of rounds 1–3.
Lean + JEV is installable since the Unreleased change (see [jev-integration](../jev-integration/README.md#lean--jev)).
Round 4 (3 repetitions) measured it: same success as lean, 1.02–1.43 × its cost; it stays opt-in.

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
| Quality gate | Prose only | Stop hook runs `make test`/`make lint` when files changed and asks once for a CHANGELOG entry. PreToolUse guard denies secrets, force push, and `rm -rf` outside the project, and asks before production access |
| Codex skills | `.agent/skills` (Codex does not read it) | `.agents/skills` |
| Installed workflows | Include the mermaid diagram | Diagram removed (still in the source and docs site) |

### Profiles

- `agentic install --profile lean` (default): two helper subagents and the native main session.
- `agentic install --profile team`: the v1 role team, `product-owner` as main session, Codex override.
- JEV works with both profiles. Under `lean` it suggests a workflow as a checklist and routes subagent models;
  it does not start role agents. Under `team` it also delegates to the role agents.
- The profile is saved in `.agentic.json` (`settings.profile`) and replayed by `agentic upgrade`.

### Quality gate

- Runtime: `.agent/gate/gate.py`, standard library only. Claude Code and Codex call it from native
  `Stop` and `PreToolUse` hooks. OpenCode calls it from `.opencode/plugins/agentic-gate.ts`.
- Stop: no changed files → no checks. Changed files → run the commands from `.agent/gate.json`
  (`{"commands": [...], "changelog": true, "max_blocks": 3}`), or by default `make test` and `make lint` when
  those targets exist. A failure returns `{"decision": "block", "reason": <command + last 40 lines>}`, so the
  agent continues with the output. Source changes without a new CHANGELOG line are asked about once per
  session. After `max_blocks` consecutive blocks, the gate lets the agent stop and report.
- Install baseline: install and upgrade write `.agentic/gate/baseline.json` with the hashes of the files that are
  uncommitted at that moment (the installed artifacts, `.gitignore`, earlier work). A file that still matches its
  hash is not a change, so a session that only reads code runs no checks.
- Guard: denies `.env*` (except `.example`, `.sample`, `.template`), private keys, `git push -f/--force`,
  and recursive deletes outside the project and the system temp directory.
- Production guard (`guard` in `.agent/gate.json`): before a Bash command that may touch production, the gate
  asks the user. The default rules (on unless `guard.defaults` is `false`):
  - `kubectl`, `helm`, or `oc` with `--context`/`--kube-context` whose value matches `guard.prod_context_pattern`
    (regex, case-insensitive, default `prod`), and `kubectl config use-context <prod>`;
  - `kubectl`, `helm`, or `oc` without a context flag when `kubectl config current-context` (local, 2 s timeout,
    failures ignored; honours `--kubeconfig` and `KUBECONFIG=`) matches the same pattern;
  - `psql`, `pg_dump`, `pg_restore`, `mysql`, or `mysqldump` whose host (`-h`, `--host`, `PGHOST=`, a
    `postgresql://`/`mysql://` URI, `host=`) matches a regex in `guard.prod_hosts` (default empty, no rule).

  `guard.confirm` adds custom rules to the defaults: a list of `{"pattern": <regex on the Bash command>,
  "reason": <text>}`. Set `guard.defaults` to `false` to turn the default rules off. Example:

  ```json
  {"guard": {"prod_context_pattern": "prod|live", "prod_hosts": ["^db\\.example\\.com$"],
             "confirm": [{"pattern": "\\bterraform\\s+apply\\b", "reason": "terraform apply changes infrastructure"}]}}
  ```

  Host behaviour: Claude Code gets `permissionDecision: "ask"` and shows the reason in its approval prompt.
  OpenCode sets the permission effect to `ask` (it never relaxes a `deny`). Codex PreToolUse hooks do not
  support `ask` (Codex 0.153 rejects it as `unsupported permissionDecision:ask`), so on Codex, and when
  the host is unknown, the rule denies the command and tells the agent to ask the user to run it themselves.
  The hooks pass `--host claude|codex|opencode`; without it, `CLAUDE_PROJECT_DIR` marks Claude Code.
- Evidence: `.agentic/gate/last.json`, written on every Stop:

  | Field | Meaning |
  |---|---|
  | `time`, `session` | Local time and host session id |
  | `changed` | Changed files (first 50), install baseline excluded |
  | `checks` | `{command, exit, seconds, tail}` per check command |
  | `passed` | No failure and no CHANGELOG request in this run (kept for compatibility) |
  | `released` | Text, present only when `max_blocks` let the agent stop with an open failure |
  | `accepted` | `true` only for `checks_passed` and `no_changes` |
  | `reason_code` | `no_changes`, `checks_passed` (changes, checks green or none configured), `checks_failed` (blocked), `changelog_missing` (blocked, asked once), `max_blocks` (released with an open failure) |
  | `head` | `git rev-parse HEAD`, `null` outside git or before the first commit |
  | `pack_version` | `.agentic.json` `_agentic.updated_by` (the installer version, for example `v2.2.0`), or `null` |
  | `profile` | `.agentic.json` `settings.profile`, or `null` |

  On a `max_blocks` release, `.agentic/gate/state.json` also stores `last_release`
  (`{time, cause, head}`, where `cause` is `checks_failed` or `changelog_missing`) for the session. On Claude Code
  the Stop hook also returns `{"systemMessage": "Agentic gate: NOT ACCEPTED (max_blocks)"}`, so the user sees it.
- `--disable-gate` removes the managed hook groups and the runtime. `--enable-gate` restores them.

## Acceptance criteria

Arms: A0 = plain host, A1 = v1.6 (JEV off, built from `b92d7ef` by `make bench-v1`), A2 = v2 lean.
1 run × 3 hosts × 4 tasks T1–T4 (`tests/bench/tasks.json`). The seeded task T5 runs on A0 and A2 only
(`--tasks T5 --modes plain,lean`); the report keeps it out of the per-mode medians and shows it in its own table. With one run per cell, pass rate is only a guard.
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
  that already fails `make lint` (the suite is green, so only an agent or gate that runs lint sees it), T6
  multi-module bugfix (the symptom is in `orders.py`; the causes are in `pricing.py` and in the tax base), T7
  multi-module feature (`Stock.reserve_many` plus a CLI command; hidden tests check that lines with the same SKU
  count together and that the existing over-reservation bug does not leak into the new API).
- Seeds: a task with `seed` in `tasks.json` copies `tests/bench/<seed>` over the fixture before the first
  commit. T5 and T6 use it, so the other tasks keep the base fixture.
- Allowlists include the version file and `docs/`, because the pack's own completion contract requires them.
- Arms (`--modes`): `plain`, `lean`, `lean-jev`, `team-jev` by default; also `team` and `v1` (v1.6 binary from
  `make bench-v1`). A `-jev` arm installs with `--enable-jev`; `JEV_API_URL` overrides the endpoint.
- Repetitions: `--reps N` runs every host × task × arm N times. The cell order is shuffled with `--seed`
  (default 0), so no arm always runs right after another and reuses its prompt cache.
- Projects: one stable path per host and arm (`/tmp/agentic-bench/<host>-<arm>`), because Codex trusts hooks
  per absolute path. Before each Claude cell the benchmark deletes `~/.claude/projects/<path>/` (transcripts and
  auto-memory), so no cell sees notes from an earlier one. Each cell copies the finished project into
  `<out>/<cell>/project`; `make bench-regrade` grades that copy.
- Invalid cells: a host that reports no token usage, a `-jev` cell without a JEV decision record, or a Codex
  cell whose hooks have no trust record is `harness_error`. It is not counted as a failure, and the next
  `make bench` with the same `BENCH_OUT` runs it again, as it does for `quota_exhausted`. A provider quota stop
  pauses only that host.
- Re-runs: `make bench` skips any cell that already has a valid `result.json`. For a new round, set a new output
  folder, for example `BENCH_OUT=.agentic-blackbox/bench-r4`.
- Commands: `make bench-v1`, `make bench-prepare`, `make bench BENCH_ARGS="--reps 3"` (paid),
  `make bench-regrade`, `make bench-report` (Markdown and `summary.json`). Results: `.agentic-blackbox/bench/`
  (Git-ignored).
- Tokens: Full = uncached + cached; uncached counts output too. Uncached alone follows prompt-cache hits between
  runs: Codex lean T3 was 12.2k vs 7.5k uncached, but 56.0k vs 56.9k full. The report shows median and IQR.
  Claude runs use `--strict-mcp-config`, because an account MCP connector attached to one arm only.
- Cost: Claude reports `total_cost_usd`. Codex and OpenCode on a ChatGPT plan report none; the report estimates
  an API-equivalent cost only for models with a price in `tests/bench/prices.json` and leaves it empty
  otherwise. Prices (2026-10-23, secondary sources listed in the file): `gpt-6-astra` $10 / $1 cached / $50 output,
  `gpt-6-luna` $0.10 / $0.01 / $0.50 per 1M tokens. Cost includes the JEV API at $0.042 per 1M input tokens
  (output free); the report also shows it alone (JEV $). Cost per success = total cost of the arm's cells /
  accepted cells.
- Models: `--model host=model` and `--effort codex=<level>`. OpenCode JEV routing stays on the provider of the
  coordinator model (`AGENTIC_JEV_MODEL_PROVIDER` overrides it). A routed model without a price in `prices.json`
  leaves the cell cost empty.
- Codex runs project hooks only after `/hooks` trust per absolute path. Run
  `make bench-prepare BENCH_ARGS="--hosts codex --modes lean,lean-jev,team-jev"`, open `codex` in each printed
  project, and trust the hooks in `/hooks`. The command prints `untrusted_hooks` per project.
- Decision rule for lean + JEV (fixed before round 4): recommend it only if, on a host, its success rate is not
  below lean (the Wilson intervals overlap or lean + JEV is higher) and its cost per success is at most 1.1 ×
  lean, with no worse success rate on the other hosts. Otherwise it stays opt-in, with no savings claimed.

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

The lean results and the K1–K8 verdict are in [results.md](results.md). A cross-mode summary (plain, SDLC with and without JEV, lean) is in [comparison.md](comparison.md).

## Limitations

- One run per cell: pass-rate differences under one task are noise (arXiv 2602.07150).
- The fixture is small, and its prompts state the expected outcome. Plain agents pass all tasks, so the
  benchmark shows cost and guards against regressions. It does not show quality gains on hard tasks.
- The OpenCode gate continues a session through `session.prompt`. The one-shot `opencode run` client can
  exit before that follow-up turn. The guard uses permission evaluation and has no live proof yet.
- The `verified_after_edit` trace signal sees only the top-level session, and OpenCode tool events are
  only partly parsed. K5 uses the end state (`delivered_green`) instead.
- Gemini and Antigravity installs get no role agents in `lean`. Use `--profile team` there.
