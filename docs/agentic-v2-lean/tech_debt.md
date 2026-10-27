# agentic v2 lean: technical debt (open after 2026-10-21)

Each item has a source, an owner role and a done-when condition. Evidence: [results](results.md) and
the protocol in [README](README.md). The ship rule requires K3 and K4. Both fail, so items 1–6 block the
v2.0.0 release.

Status 2026-10-22, after the round 2 re-run (see [results](results.md)): items 1, 2, 4, 5, 6 and 14 are done.
K3 passes; K4 still fails on T3 tokens, so item 3 stays open and blocks the release. The external review of the
results (GPT `sol-6.1`) agrees with items 1–3 and adds items 17–19. Round 2 adds item 20.

## Release blockers (next iteration)

| # | Item | Source | Owner | Done when |
| --- | --- | --- | --- | --- |
| 1 | **Done (round 2).** **Rule tables invite eager reads.** Codex T2 read `general-dev-tools/SKILL.md`, `security.md`, `readme-sync-guide.md` and `git-workflow-guide.md` for a small pure-function change. | results, root cause 1 | team-lead | Spec `AGENTS.md` files (`software/general`, `software/backend`) have no rule tables. Claude uses `paths:`. On Codex and OpenCode, only the skills and workflows that need a rule link it. The re-run cells show no reads of unrelated rules. |
| 2 | **Done (round 2): no explorer; the 2 subagents are the core's reviewer.** **Native explorer spawn on a tiny repository.** In Codex T2, the native `explore` subagent used 47.8k uncached tokens on a 200-line fixture, and the cell hit the 80k cap. | results, root cause 2 | team-lead | The core says not to start an explorer for a repository you can list with one command. The re-run Codex T2 has 0 subagents and is accepted. |
| 3 | **Open: K4 fails in round 2 (T3 uncached 1.20 / 3.28 / 1.29 × plain).** **Rules read without need.** The core does not limit reads of on-demand guidance to the task subject. | results, root cause 1 | product-owner | The core says: "Read a rule or skill only when the task touches its subject." K4 holds: T3 costs ≤ 1.2 × plain on every host. |
| 4 | **Done (round 2).** **Version bump on bugfixes.** Lean agents sometimes bump the version on T1/T4. The core requires a version bump only for a completed feature. | results, root cause 3 | product-owner | The core says a bugfix updates `CHANGELOG.md` only. The T1/T4 re-runs change no version file. |
| 5 | **Done (round 2): Claude T3 input is 1.11 × plain.** **Fixed startup overhead above the always-on estimate.** On T3, lean cost +3k (Claude), +4.7k (Codex) and +2.8k (OpenCode) uncached over plain. Hooks add no context: Stop and PreToolUse print only when they block. Codex and OpenCode differences are prompt-cache noise: full input on T3 is 56.0k vs 56.9k (Codex) and 9.2k vs 15.9k (OpenCode). Claude is real: +2.9k per request, partly because an account MCP connector attached to the lean cell only. The benchmark now reports full input and runs Claude with `--strict-mcp-config`. | results, root cause 4 | developer | The item 6 re-run shows Claude T3 input ≤ 1.2 × plain, or the remaining gap is traced to named context parts. |
| 6 | **Done (round 2, Codex on `gpt-6-astra`).** **Targeted re-run.** | results, next iteration | qa | Codex T2, T3 on all three hosts (A0 and A2, because the metric and isolation changed), OpenCode T4, and T5 on A0/A2 × 3 hosts are re-run. If K3 and K4 pass, the full A2 row runs again and `results.md` is updated. |

## Product and runtime

| # | Item | Source | Owner | Done when |
| --- | --- | --- | --- | --- |
| 7 | **OpenCode Stop gate depends on a live server.** The plugin continues a session through `session.prompt`, and the one-shot `opencode run` client can exit first. OpenCode T4 left no gate evidence. | results, README limitations | developer | A live OpenCode run shows a blocked turn that continues with the gate reason, or the plugin switches to a hook that runs before the turn ends. |
| 8 | **OpenCode guard is not proven live.** It uses `permission.evaluate`, which may not fire for auto-allowed tools. | README limitations | developer | A live run denies a `.env` read, and an offline plugin test with a stubbed `@opencode/plugin` covers it. |
| 9 | **No `assisted` profile for OpenCode.** The plan proposed a compact task → skill index for weaker harnesses. It was not built, because the spec `AGENTS.md` indexes cover it for now. | plan, phase 4 | product-owner | A measured OpenCode benefit, or a decision recorded here to drop the idea. Item 1 removes the current indexes, so this must be decided with item 1. |
| 10 | **Gemini and Antigravity get no agents in `lean`.** | README limitations | devops-engineer | Either lean agents ship for these hosts, or the installer selects `team` for them. |
| 11 | **`assess-areas` still counts files, not tokens.** `make lint` now fails above 4k always-on tokens, but the area scorecard `token_efficiency` does not use the measurement. | plan, phase 5 | developer | `scripts/assess_area_quality.py` reads the `context_budget.py` estimate per host. |
| 12 | **Only `software/general` and `software/backend` are lean.** Other areas keep always-on rules and role delegation in workflows. | scope decision | team-lead | Each other area passes `make context-budget CONTEXT_BUDGET_MAX=4000` with its own selection. |
| 20 | **Fixed for `lean`: explorer and reviewer inherit the session model. Open for `team` and JEV tiers.** **Installed Codex agents pin models the account may not serve.** `extensions/codex/model-tiers.json` maps `balanced` to `gpt-6.1-sol` and `fast` to `gpt-6-luna`; the installer writes them into `.codex/agents/reviewer.toml` and `explorer.toml`. On 2026-10-22 a ChatGPT account no longer served either model. In round 2, Codex T2 lean started the reviewer on `gpt-6.1-sol`, got 0 tokens, and retried on the session model. | results, round 2 | developer | The installed agents inherit the session model, or the installer checks the tiers against the models the account serves. |
| 21 | **JEV routes Codex helper spawns to a frontier model.** In round 4, Codex lean + JEV sent 4 helper spawns to `gpt-6-astra` while the session ran `gpt-5.6-terra`; cost per accepted task rose to 1.43 × lean at the same success rate. Team + JEV sent 18 spawns there and hit the token cap twice. | results, round 4 | developer | Under `lean`, routing of `explorer` and `reviewer` never picks a tier above the session model, and round 4 Codex lean + JEV costs ≤ 1.1 × lean. **Routing part fixed:** helpers are capped at the session tier (`balanced` when unknown) and fall back with `tier_above_session`; the paid cost check is still open. |

## Evaluation

| # | Item | Source | Owner | Done when |
| --- | --- | --- | --- | --- |
| 13 | **Single run per cell.** Pass-rate differences under one task are noise (arXiv 2602.07150). | protocol | team-lead | At least three runs per cell for any release claim on tokens or acceptance. |
| 14 | **Done (round 2): plain fails T5 on Claude and OpenCode, lean passes everywhere.** **Tasks are too easy to show gate value.** Plain agents pass all 12 tasks, and the gate never blocked. | results | qa | A task with a hidden failing check that agents tend to skip (for example, a lint error in a touched file) is added. The A0/A2 difference in `delivered_green` is reported. |
| 15 | **Trace signals are partial.** `verified_after_edit` sees only the top-level session. Codex child commands live in rollout files. | README limitations | developer | The benchmark reads child sessions on Codex and OpenCode, or the signal is removed from the report. |
| 16 | **Codex hook trust is manual.** Each benchmark path needs `/hooks` trust before a lean run. | protocol | devops-engineer | The protocol documents a one-time trust step per stable path (done in README). A check refuses to start a Codex lean cell when its hooks are untrusted, as `pilot_jev.trust_ok` does. |
| 17 | **Hard tasks where plain agents fail.** T1–T5 are small. The review asks for multi-module bugs, an architecture change, and tasks with a quality check that plain agents sometimes miss. | external review, point 3 | qa | At least two such tasks exist with self-tested graders, and A0 fails at least one of them in a pilot run. |
| 18 | **OpenCode lean overhead is real.** By full input, lean is 1.93 × plain on OpenCode (Claude 1.55 ×, Codex 1.12 ×), and lean costs more than v1 there. The sources are not split yet: skill and command listings from three skill folders, the gate plugin, and the native `explore`/`general` agents. | external review, point 2; results | developer | A per-source breakdown of the first OpenCode request exists, and the largest source is removed or justified. |
| 19 | **Implemented (Unreleased); measured in results.md round 4: opt-in, no gain.** **JEV always forces `team`.** `profile::is_team` returns true when JEV is on, so every JEV task gets nine SDLC roles. The review asks for an adaptive choice: `lean` for questions and bugfixes, `team` for features and epics. | external review, point 4; `src/profile.rs` | product-owner | A JEV benchmark compares forced `team` with adaptive selection on a bugfix and a feature, and the decision is recorded here. |

## Done in this iteration

- Windows CI (`test (windows-latest)`, PR #77): `is_manual_rule` and `strip_agent_diagram` did not parse CRLF
  checkouts, so manual rules landed in `.claude/rules/`. Both now normalize line endings.
