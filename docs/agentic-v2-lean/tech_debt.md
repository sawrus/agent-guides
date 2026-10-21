# agentic v2 lean: technical debt (open after 2026-10-21)

Each item has a source, an owner role and a done-when condition. Evidence: [results](results.md) and
the protocol in [README](README.md). The ship rule requires K3 and K4. Both fail, so items 1–5 block the
v2.0.0 release.

## Release blockers (next iteration)

| # | Item | Source | Owner | Done when |
| --- | --- | --- | --- | --- |
| 1 | **Rule tables invite eager reads.** Codex T2 read `general-dev-tools/SKILL.md`, `security.md`, `readme-sync-guide.md` and `git-workflow-guide.md` for a small pure-function change. | results, root cause 1 | team-lead | Spec `AGENTS.md` files (`software/general`, `software/backend`) have no rule tables. Claude uses `paths:`. On Codex and OpenCode, only the skills and workflows that need a rule link it. The re-run cells show no reads of unrelated rules. |
| 2 | **Native explorer spawn on a tiny repository.** In Codex T2, the native `explore` subagent used 47.8k uncached tokens on a 200-line fixture, and the cell hit the 80k cap. | results, root cause 2 | team-lead | The core says not to start an explorer for a repository you can list with one command. The re-run Codex T2 has 0 subagents and is accepted. |
| 3 | **Rules read without need.** The core does not limit reads of on-demand guidance to the task subject. | results, root cause 1 | product-owner | The core says: "Read a rule or skill only when the task touches its subject." K4 holds: T3 costs ≤ 1.2 × plain on every host. |
| 4 | **Version bump on bugfixes.** Lean agents sometimes bump the version on T1/T4. The core requires a version bump only for a completed feature. | results, root cause 3 | product-owner | The core says a bugfix updates `CHANGELOG.md` only. The T1/T4 re-runs change no version file. |
| 5 | **Fixed startup overhead above the always-on estimate.** On T3, lean costs +3k (Claude), +4.7k (Codex) and +2.8k (OpenCode) over plain. The estimate is 1.5–1.9k. Hook and tool descriptions are not measured. | results, root cause 4 | developer | `context_budget.py` also counts the hook and agent definitions. Root `AGENTS.md` and `CLAUDE.md` are shortened until T3 ≤ 1.2 × plain. |
| 6 | **Targeted re-run.** | results, next iteration | qa | Codex T2, T3 on all three hosts, and OpenCode T4 are re-run: 6 paid cells. If K3 and K4 pass, the full A2 row (12 cells) runs again and `results.md` is updated. |

## Product and runtime

| # | Item | Source | Owner | Done when |
| --- | --- | --- | --- | --- |
| 7 | **OpenCode Stop gate depends on a live server.** The plugin continues a session through `session.prompt`, and the one-shot `opencode run` client can exit first. OpenCode T4 left no gate evidence. | results, README limitations | developer | A live OpenCode run shows a blocked turn that continues with the gate reason, or the plugin switches to a hook that runs before the turn ends. |
| 8 | **OpenCode guard is not proven live.** It uses `permission.evaluate`, which may not fire for auto-allowed tools. | README limitations | developer | A live run denies a `.env` read, and an offline plugin test with a stubbed `@opencode/plugin` covers it. |
| 9 | **No `assisted` profile for OpenCode.** The plan proposed a compact task → skill index for weaker harnesses. It was not built, because the spec `AGENTS.md` indexes cover it for now. | plan, phase 4 | product-owner | A measured OpenCode benefit, or a decision recorded here to drop the idea. Item 1 removes the current indexes, so this must be decided with item 1. |
| 10 | **Gemini and Antigravity get no agents in `lean`.** | README limitations | devops-engineer | Either lean agents ship for these hosts, or the installer selects `team` for them. |
| 11 | **`assess-areas` still counts files, not tokens.** `make lint` now fails above 4k always-on tokens, but the area scorecard `token_efficiency` does not use the measurement. | plan, phase 5 | developer | `scripts/assess_area_quality.py` reads the `context_budget.py` estimate per host. |
| 12 | **Only `software/general` and `software/backend` are lean.** Other areas keep always-on rules and role delegation in workflows. | scope decision | team-lead | Each other area passes `make context-budget CONTEXT_BUDGET_MAX=4000` with its own selection. |

## Evaluation

| # | Item | Source | Owner | Done when |
| --- | --- | --- | --- | --- |
| 13 | **Single run per cell.** Pass-rate differences under one task are noise (arXiv 2602.07150). | protocol | team-lead | At least three runs per cell for any release claim on tokens or acceptance. |
| 14 | **Tasks are too easy to show gate value.** Plain agents pass all 12 tasks, and the gate never blocked. | results | qa | A task with a hidden failing check that agents tend to skip (for example, a lint error in a touched file) is added. The A0/A2 difference in `delivered_green` is reported. |
| 15 | **Trace signals are partial.** `verified_after_edit` sees only the top-level session. Codex child commands live in rollout files. | README limitations | developer | The benchmark reads child sessions on Codex and OpenCode, or the signal is removed from the report. |
| 16 | **Codex hook trust is manual.** Each benchmark path needs `/hooks` trust before a lean run. | protocol | devops-engineer | The protocol documents a one-time trust step per stable path (done in README). A check refuses to start a Codex lean cell when its hooks are untrusted, as `pilot_jev.trust_ok` does. |
