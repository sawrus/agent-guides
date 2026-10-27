---
covers:
  - AGENTS.md
  - MEMORY.md
  - src/profile.rs
  - src/gate.rs
  - extensions/codex/hooks/gate/**
  - extensions/opencode/plugins/agentic-gate.ts
  - scripts/bench_sdlc.py
  - scripts/context_budget.py
  - extensions/*/agents/explorer.*
  - extensions/*/agents/reviewer.*
---

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
| Quality gate | Prose only | Stop hook runs `make test`/`make lint` when files changed and asks once for a CHANGELOG entry. PreToolUse guard denies secrets, force push, and `rm -rf` outside the project, asks before production access, and blocks write SQL on non-local databases |
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
  `Stop`, `PreToolUse`, and `SessionStart` hooks. OpenCode calls it from `.opencode/plugins/agentic-gate.ts`.
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
- Database guard (`guard.db` in `.agent/gate.json`, default `{"mode": "ask", "write": "deny"}`): checks every
  Bash command. It reads the command, its heredoc bodies, and the first 256 KB of up to 8 script files that the
  command runs (`python*`, `node`, `bash`, `sh`, `ruby`, `psql -f`, followed by an existing `.py`, `.js`, `.sh`,
  `.sql`, or `.rb` path; relative paths resolve from the project directory or a preceding `cd <dir>`).
  - Connection: `psycopg`/`psycopg2` `connect`, `asyncpg.connect`/`create_pool`, `create_engine(`,
    `pymysql.connect`, `mysql.connector.connect`, `redis.Redis(`/`redis.from_url`, `pymongo.MongoClient`,
    `clickhouse_connect`, or a CLI client (`psql`, `pg_dump`, `pg_restore`, `mysql`, `mysqldump`, `redis-cli`,
    `mongosh`, `clickhouse-client`).
  - Credentials from the environment: `load_dotenv`, `dotenv_values`, `find_dotenv`, `dotenv ... config`,
    `source <x>.env`, `. ./.env`, `--env-file`, `$(cat .env)`, `os.environ[...]`/`os.getenv(...)`/`process.env`
    or `$VAR` with a name that contains `DSN`, `DATABASE_URL`, `DB_`, `PG`, `PSQL`, `MYSQL`, `REDIS`, or `MONGO`.
  - Local target: every host found (`-h`, `--host`, `host=`, the host in a `postgresql://`, `mysql://`,
    `redis://`, `mongodb://`, or `clickhouse://` URL) is `localhost`, `127.*`, `::1`, `0.0.0.0`,
    `host.docker.internal`, or a unix socket path; or `sqlite` is the only target; or a CLI client has no host
    flag and no `$VAR` argument (it uses the local default, or `PGHOST`/`MYSQL_HOST` from the gate's environment).
    Credentials from the environment make the target unknown, because the gate does not read `.env`.
  - Write or maintenance statement (case-insensitive): `VACUUM`, `ANALYZE` (not `EXPLAIN ANALYZE` or
    `EXPLAIN (ANALYZE ...)`), `REINDEX`, `CLUSTER`, `REFRESH MATERIALIZED VIEW`, `DROP <object>`, `TRUNCATE`,
    `DELETE FROM`, `UPDATE <t> SET`, `INSERT INTO`, `MERGE INTO`, `ALTER TABLE|INDEX|SYSTEM|DATABASE|ROLE|...`,
    `CREATE [UNIQUE] INDEX`, `CREATE TABLE|EXTENSION|ROLE|USER|SCHEMA|DATABASE`, `GRANT`/`REVOKE <privilege>`,
    `COPY <t> FROM`, `pg_terminate_backend`, `pg_cancel_backend`, `default_transaction_read_only = off`,
    `TRANSACTION READ WRITE`; Redis `FLUSHALL`, `FLUSHDB`, `DEL`; Mongo `.drop()`, `deleteMany`, `updateMany`.

  | Case | Decision |
  |---|---|
  | Local target | No decision |
  | Non-local or unknown target + write or maintenance statement | `deny` on every host (`guard.db.write: "ask"` asks instead) |
  | Host in plan (read-only) mode + non-local or unknown target | `deny` |
  | Credentials from the environment + read-only statements | `ask` (`guard.db.mode: "deny"` denies) |
  | Unknown target, no credentials from the environment, read-only | No decision |

  `guard.db.mode: "off"` turns the database guard off. `guard.defaults: false` does not turn it off. A `deny`
  tells the agent to show the statement to the user and let them run it. An `ask` behaves as the production
  guard: Codex denies and tells the agent to ask the user to run the command. Plan mode: Claude Code
  `permission_mode: "plan"` in the PreToolUse payload; OpenCode, the built-in `plan` agent (the plugin passes the
  agent id). Codex hooks do not show a mode.
- OpenCode enforcement: the plugin runs the guard in the `permission.evaluate` hook. OpenCode (checked in 2.0.29)
  runs that hook for every permission check that no rule denies, also when the effect is `allow`, and the shell
  tool checks the `shell` permission for every command except a plain `cd`. So the guard runs for every shell
  call, also under the build agent that auto-allows shell. A `deny` sets the effect to `deny` (OpenCode blocks
  the call and returns the reason to the agent). An `ask` turns `allow` into `ask` (OpenCode shows its permission
  prompt with the reason) and never relaxes a `deny`. Calls that an OpenCode rule already denies skip the hook.
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
- Stale-checkout notice (`--event start`): at session start the runtime reads local git refs (no fetch) and,
  only when the checkout looks stale, adds one line of context. The rule and text match the install and upgrade
  warning; see [stale-checkout warning](../agentic-usage.md#stale-checkout-warning). Claude Code and Codex call
  it from a native `SessionStart` hook (matcher `startup|resume`, output
  `hookSpecificOutput.additionalContext`; Codex 0.153 accepts this event and field). OpenCode runs it once per
  session from the `session.hook("context")` callback and appends the line to the request system parts.
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
  count together and that the existing over-reservation bug does not leak into the new API), T8 bugfix with a
  hidden defect (`Stock.release` lets the reservation go negative; the prompt states the criterion "release only
  lowers the reservation". The suite and lint stay green. The obvious fix checks only "more than reserved"; the
  hidden tests also reject a negative quantity, which a careful review of the diff against the criterion
  catches), T10 question that needs a rule (which standard Makefile targets from the installed
  `makefile-guide` rule are missing; the answer must name `make install`, `make dev`, `make fmt`, and
  `make clean`; no changes allowed).
- Seeds: a task with `seed` in `tasks.json` copies `tests/bench/<seed>` over the fixture before the first
  commit. T5, T6, and T8 use it, so the other tasks keep the base fixture.
- Allowlists include the version file and `docs/`, because the pack's own completion contract requires them.
- Arms (`--modes`): `plain`, `lean`, `lean-jev`, `team-jev` by default; also `lean-noreviewer`, `team`, and `v1`
  (v1.6 binary from `make bench-v1`). A `-jev` arm installs with `--enable-jev`; `JEV_API_URL` overrides the
  endpoint. `lean-noreviewer` installs `lean` and then deletes the reviewer agent (`.claude/agents/reviewer.md`,
  `.codex/agents/reviewer.toml`, `.opencode/agents/reviewer.md`, the `reviewer` entry in `.opencode/opencode.json`,
  and an `[agents.reviewer]` table in `.codex/config.toml` if one exists) before the install commit. The core
  text in `AGENTS.md` stays the same, so the agent can still start a native subagent for a review.
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
  accepted cells. `gpt-6.1-terra` has no published price yet: `prices.json` marks it as an estimate equal to
  `gpt-5.6-terra` ($2 / $0.20 / $12).
- Gate columns: when `.agentic/gate/last.json` records `accepted` and `reason_code`, the report shows
  `Accepted by gate` and `Released` (`reason_code = max_blocks`) per cell and as `k/n` per host and mode. A gate
  without these fields shows `n/a`.
- Models: `--model host=model` and `--effort codex=<level>`. OpenCode JEV routing stays on the provider of the
  coordinator model (`AGENTIC_JEV_MODEL_PROVIDER` overrides it). A routed model without a price in `prices.json`
  leaves the cell cost empty.
- Codex runs project hooks only after `/hooks` trust per absolute path. Run
  `make bench-prepare BENCH_ARGS="--hosts codex --modes lean,lean-jev,team-jev"`, open `codex` in each printed
  project, and trust the hooks in `/hooks`. The command prints `untrusted_hooks` per project.
- Decision rule for lean + JEV (fixed before round 4): recommend it only if, on a host, its success rate is not
  below lean (the Wilson intervals overlap or lean + JEV is higher) and its cost per success is at most 1.1 ×
  lean, with no worse success rate on the other hosts. Otherwise it stays opt-in, with no savings claimed.

### Round 6 decision rules (fixed before the run)

Source: [plan](../agentic-orchestration-research/plan.md) steps 0 and 4, experiment E1 in
[experiments](../agentic-orchestration-research/experiments.md). Hosts: Codex with `--model codex=gpt-6.1-terra`
(the Codex session model of round 6; `pilot_jev.COORDINATOR` keeps its default, so pass the flag on every Codex
command) and Claude (`sonnet`). One output folder for the round: `BENCH_OUT=.agentic-blackbox/bench-r6`. A cell
that already has a valid result is not run again, so later commands reuse earlier cells. The cell counts below
are paid cells; each hypothesis spends at most 30. `harness_error` and `quota_exhausted` cells run again and do
not count.

Before the first paid command (no model calls), create the projects and trust the Codex hooks in `/hooks`:

```bash
make bench-prepare BENCH_OUT=.agentic-blackbox/bench-r6 BENCH_ARGS="--hosts codex --modes lean,lean-noreviewer,lean-jev"
```

Run order: H4, then H0, then H-clean "before". H-clean "after" runs only after the content cleanup is merged.

**H4: the reviewer earns its place in the lean default.** Precondition: plan steps 0–2 are merged.

```bash
make bench BENCH_OUT=.agentic-blackbox/bench-r6 BENCH_ARGS="--hosts codex --tasks T8 --modes lean,lean-noreviewer --reps 9 --model codex=gpt-6.1-terra"  # 18 cells
make bench BENCH_OUT=.agentic-blackbox/bench-r6 BENCH_ARGS="--hosts claude --tasks T8 --modes lean,lean-noreviewer --reps 3"  # 6 cells
```

Total: 24 paid cells. Rule: the reviewer stays in the lean default only if, on Codex T8, `lean` accepted ≥
`lean-noreviewer` accepted + 2 (of 9), and the total cost of the 9 `lean` cells ≤ 1.3 × the total cost of the 9
`lean-noreviewer` cells. Claude is a guard: `lean` accepted on T8 must not be below `lean-noreviewer`. If any
part fails, the reviewer leaves the lean default, and plan step 2 continues for `explorer` only.

**H0: after the JEV tier-cap fix, no lean helper gets a model above the session tier.** Precondition: plan step 0
is merged.

```bash
make bench BENCH_OUT=.agentic-blackbox/bench-r6 BENCH_ARGS="--hosts codex --tasks T6,T7,T8 --modes lean,lean-jev --reps 3 --model codex=gpt-6.1-terra"  # 18 cells, 15 paid (lean T8 r1-r3 come from H4)
make bench BENCH_OUT=.agentic-blackbox/bench-r6 BENCH_ARGS="--hosts claude --tasks T6,T7,T8 --modes lean,lean-jev --reps 3"  # 18 cells, 15 paid (lean T8 r1-r3 come from H4)
```

Total: 30 paid cells. Check every `lean-jev` cell: each helper row in `tokens.agents` (Codex: `agent_path` other
than `/root`; Claude: a model other than the session model) and each JEV `spawn` or `observation` record in
`jev.decisions` names a model. Session tier: Codex `gpt-6.1-terra` = `balanced` (`extensions/codex/model-tiers.json`),
Claude `sonnet` = `balanced`. A model is above the session tier when its tier is `frontier` (`gpt-6-astra`,
`opus`), or, for a model without a tier, when its input price in `tests/bench/prices.json` is above the session
model's price. Rule: H0 holds if no helper on any host gets a model above the session tier. With fewer than 3
helper spawns on a host, H0 is inconclusive for that host; no claim is made. Secondary check from plan step 0:
Codex `lean-jev` cost per accepted task ≤ 1.1 × `lean` on T6–T8 at a success rate not below `lean`.

**H-clean: the planned content cleanup does not lower lean results and saves tokens.** Tasks: T1–T7 and T10.

```bash
# before the cleanup (the current build)
make bench BENCH_OUT=.agentic-blackbox/bench-r6 BENCH_ARGS="--hosts codex --tasks T1,T2,T3,T4,T5,T6,T7,T10 --modes lean --model codex=gpt-6.1-terra"  # 8 cells, 6 paid (T6, T7 r1 come from H0)
make bench BENCH_OUT=.agentic-blackbox/bench-r6 BENCH_ARGS="--hosts claude --tasks T1,T2,T3,T4,T5,T6,T7,T10 --modes lean"  # 8 cells, 6 paid (T6, T7 r1 come from H0)
# after the cleanup is merged and built
make bench BENCH_OUT=.agentic-blackbox/bench-r6-clean BENCH_ARGS="--hosts codex --tasks T1,T2,T3,T4,T5,T6,T7,T10 --modes lean --model codex=gpt-6.1-terra"  # 8 cells
make bench BENCH_OUT=.agentic-blackbox/bench-r6-clean BENCH_ARGS="--hosts claude --tasks T1,T2,T3,T4,T5,T6,T7,T10 --modes lean"  # 8 cells
```

Total: 28 paid cells. Compare the `r1` cells of the same tasks on each host. Rule: the cleanup ships if, on each
host, `lean` after accepted ≥ `lean` before accepted, and the sum of full tokens (uncached + cached) after ≤ 0.9 ×
before. Otherwise the cleanup is revised before release. With one repetition, a one-task difference in accepted
cells is noise; the token rule carries the decision.

## Results

### K1 (offline, `software.backend,software.general`)

| Host | v1.6 | v2 lean | Change |
|---|---|---|---|
| Claude | 12,153 | 1,936 | −84% |
| Codex | 9,420 | 1,495 | −84% |
| OpenCode | 10,808 | 1,766 | −84% |

Estimate: UTF-8 bytes / 4 over instruction files and imports, unscoped rules, the main agent prompt, and
skill, agent, and command descriptions.

### Content cleanup measurement (offline)

The content cleanup (docs/artifact-standard.md) deleted `software.platform`, `software.full-stack`, every prompt,
63 of 73 workflows, 84 of 98 skills, and 23 of 86 rules (merged into survivors), and cut every remaining rule to scoped, checkable items. Before = base branch
`feat/AGV2-check-artifacts`; after = `feat/AGV2-content-cleanup`; same debug binary. Commands:
`python3 scripts/context_budget.py --all-selections` (always-on tokens per host, ART-B1 limit 4,000) and a sum of
UTF-8 bytes / 4 over the `rules/`, `skills/`, `workflows/`, and `prompts/` files of a selection.

Installed content for `devops.infrastructure,devops.observability,software.backend,software.general`:

| Bucket | Before: files · tokens | After: files · tokens |
|---|---|---|
| Rules | 22 · 8,918 | 22 · 7,374 |
| Skills (all files) | 16 · 21,128 | 5 · 3,567 |
| Workflows | 17 · 23,317 | 6 · 3,546 |
| Prompts | 17 · 15,876 | 0 · 0 |
| **Total** | **72 · 69,239** | **33 · 14,487 (−79%)** |

Always-on tokens of the same selection: Claude 6,782 → 2,118, Codex 2,769 → 1,794, OpenCode 3,250 → 1,947.

Always-on tokens per selection (`total` column of `context_budget.py`):

| Selection | Claude before | Claude after | Codex before | Codex after | OpenCode before | OpenCode after |
|---|---:|---:|---:|---:|---:|---:|
| `devops.ci-cd` | 3361 | 1407 | 1672 | 1215 | 1772 | 1237 |
| `devops.database-ops` | 2919 | 1289 | 1633 | 1126 | 1688 | 1118 |
| `devops.devsecops` | 2854 | 1421 | 1628 | 1231 | 1686 | 1251 |
| `devops.infrastructure` | 4078 | 1440 | 1689 | 1247 | 1817 | 1270 |
| `devops.kubernetes` | 4622 | 1420 | 1786 | 1232 | 1910 | 1249 |
| `devops.networking` | 2801 | 1212 | 1639 | 1050 | 1695 | 1041 |
| `devops.observability` | 3235 | 1382 | 1699 | 1220 | 1793 | 1212 |
| `devops.sre` | 2897 | 1338 | 1634 | 1144 | 1724 | 1167 |
| `software.backend` | 1618 | 1371 | 1278 | 1185 | 1448 | 1201 |
| `software.data-engineering` | 3283 | 1240 | 1980 | 1077 | 2123 | 1069 |
| `software.frontend` | 3566 | 1226 | 2036 | 1063 | 2171 | 1055 |
| `software.full-stack` | 6792 | removed | 2049 | removed | 2235 | removed |
| `software.general` | 1337 | 1411 | 1101 | 1140 | 1167 | 1241 |
| `software.mlops` | 3208 | 1229 | 1824 | 1067 | 1973 | 1058 |
| `software.mobile` | 3172 | 1231 | 1868 | 1068 | 2000 | 1060 |
| `software.platform` | 3493 | removed | 2093 | removed | 2244 | removed |
| `software.qa` | 2906 | 1222 | 1728 | 1060 | 1862 | 1051 |
| `software.security` | 3772 | 1316 | 1940 | 1154 | 2075 | 1145 |
| `software.backend,software.general` | 1793 | 1618 | 1379 | 1325 | 1622 | 1448 |
| `software.frontend,software.general` | 3740 | 1473 | 2137 | 1202 | 2346 | 1303 |
| `software.full-stack,software.general` | 6967 | removed | 2150 | removed | 2410 | removed |
| `software.backend,software.frontend,software.general` | 4196 | 1680 | 2415 | 1387 | 2801 | 1510 |
| `software.backend,software.general,devops.ci-cd,devops.kubernetes` | 7452 | 2122 | 2839 | 1773 | 3321 | 1952 |
| `devops.kubernetes,devops.ci-cd,devops.observability` | 8892 | 1884 | 3156 | 1667 | 3490 | 1714 |
| `devops.infrastructure,devops.kubernetes,devops.sre` | 9273 | 1872 | 3109 | 1624 | 3467 | 1702 |
| `devops.infrastructure,devops.observability,software.backend,software.general` | 6782 | 2118 | 2769 | 1794 | 3250 | 1947 |

Every selection is now under the 4,000-token ART-B1 limit on every host; before, 8 selections were over it on
Claude. `software.general` grows by 74 tokens on Claude because it now holds the four general workflows.

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
