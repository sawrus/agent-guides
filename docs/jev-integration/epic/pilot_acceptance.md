# Comparative pilot: frozen acceptance and accounting

Frozen on 2026-10-20 before any pilot model run; the commit that adds this file precedes the first result. The runner is `scripts/pilot_jev.py`; the protocol is [pilot.md](pilot.md). Changes after the first run are recorded as deviations, never applied silently.

## Matrix

Hosts: Codex, Claude Code, OpenCode. Tasks A/B/C. Modes:

| Mode | Agentic | JEV | Workflow in prompt | Role models |
| --- | --- | --- | --- | --- |
| plain | none | — | no | host default |
| fixed | installed | off | yes (`provision-environment` / `code-review-workflow` / `develop-feature`) | installer baseline pins |
| jev | installed | on | no | JEV routing |
| workflow_only (A, C) | installed | on | no | baseline pins copied from the JEV-off install, so JEV keeps them |
| models_only (A, C) | installed | on | yes | JEV routing |

That is 27 primary and 12 ablation cells. Areas: `devops,software` with `devops.infrastructure,software.backend,software.general`. Fixed coordinator models: Codex `gpt-6.1-sol`, Claude `sonnet`, OpenCode `openai/gpt-6-luna`. Each cell runs once, and completed cells are never repeated.

## Isolation

- A and B are clean `git clone` copies of the pinned commits (A `527f1e0`, B `master@d60fe47`). Untracked `.env` and local agent files cannot enter the copy, and the remote is removed.
- C starts from an empty repository.
- Copies live under `/tmp/agentic-pilot`, outside any repository.
- Codex JEV cells reuse the hook-trusted path; the runner refuses a cell whose `hooks.json` differs from the reviewed one. No trust is written by the harness.
- Telegram notifications use the user's configuration in all installed modes.

## Limits (harness-enforced)

- Six minutes per cell, including at most one follow-up turn. The follow-up is sent only if acceptance fails, no cap fired and at least 30 seconds remain.
- 50,000 **uncached** tokens per cell across coordinator and subagents (user decision 2026-10-20). Uncached means input minus cache reads, plus cache writes and output.
- Cached reads are recorded separately.
- 1,000,000 uncached tokens per host, including earlier native checks.
- The run process group is killed when a cap fires.

Sources: Codex rollout `token_count` per session (root and children); Claude stream-json assistant usage by message id plus `total_cost_usd`; OpenCode parent `step-finish` live and child sessions through `session export` on a private server.

## Acceptance (automated, binary)

- **A**:
  - `GRAFANA_FEASIBILITY.md` exists.
  - Its first line is exactly `VERDICT: FEASIBLE` or `VERDICT: NOT FEASIBLE`.
  - It names at least three dashboard JSON files that exist under `configurations/grafana`.
  - It is the only changed file.
- **B**:
  - `REVIEW.md` exists.
  - It has 3–10 distinct `src/<path>.py:<line>` references that exist in the copy.
  - It is the only changed file.
- **C**: the independent `scripts/blackbox_calculator_probe.py` verifies addition, subtraction, multiplication, division, invalid input and division by zero.

Changes under `.agentic/` and `__pycache__/` are runtime output and ignored. Human quality review of the anonymized outputs uses the same rubric for all modes and is recorded separately.

## Reported per cell

Status (`accepted`, `rejected`, `time_cap`, `token_cap`, `blocked_untrusted_hooks`, `harness_error`), elapsed time, turns, uncached and cached tokens per agent/model, and whether coverage is complete. Also: Claude cost, JEV calls and usage, workflow and model decisions, and recommended/submitted/observed evidence. Unknown values stay unknown. No savings are claimed from single exploratory cells.
