# Comparative pilot — authorization gate CLOSED

Implementation acceptance is not budget permission. After the draft PR and implementation checks, obtain explicit human acceptance and a separate answer authorizing the comparative pilot. Do not run the matrix before both answers. Target projects are on the work host; inspect their AGENTS and current branches first. Store private path mapping outside published artifacts.

## Locked experiment

Three tasks: (A) Grafana Docker/configuration and dashboard-import feasibility, without deployment; (B) superficial Python performance/code review on master, without connecting to a database or reading its .env; (C) console calculator with four operations, input errors and division by zero, independently tested. Published labels are task A/B/C, never repository names or internal paths.

Three environments: Codex, Claude Code, OpenCode. Each has these primary modes:
1. No Agentic artifacts, hooks or workflow; preserve ordinary project instructions.
2. Run agentic upgrade, select devops/infrastructure and software/backend + general, JEV disabled; fixed workflows provision-environment / code-review-workflow / develop-feature for A/B/C.
3. Same candidate build and selected areas, JEV enabled, no explicit workflow in the task prompt.

Nine primary runs per environment = 27. Tasks A/C also receive workflow-only and models-only JEV ablations = four additional runs per environment = 12. Ablations keep other host settings identical and are recorded separately. For workflow-only, pin every native role model to the fixed-SDLC baseline in the isolated copy so JEV preserves it without a model call. For models-only, explicitly request the fixed baseline workflow so workflow selection makes no JEV call. These use existing pin/explicit-workflow contracts, without a new runtime decision switch. Verify actual logs show the intended isolation. Record permission decisions separately; if permission behavior differs, do not attribute the full outcome solely to workflow/model selection.

Use clean isolated copies of the same commit, pinned candidate version/asset hashes and one fixed coordinator model per environment. Upgrade must not silently replace the candidate with a released binary. Freeze acceptance before model runs. Do not choose acceptance based on generated answers. Workflow-fit can have several correct workflows; judge scope and installed areas. Human/code reviewers assess anonymized outputs against the same rubric.

## Budget and prompt

Per environment: 1,000,000 input+output tokens including cached input once, all subagents, repeats, corrections and already-used native blackbox quota. Per run: 50,000 tokens total, six minutes, at most one corrective turn within those limits; no quality-driven model escalation. Stop launching if telemetry or remaining budget is insufficient. Show consumed and remaining budget before asking for pilot authorization. Deviation decided by the user on 2026-10-20: the 50,000 per-run and 1,000,000 per-host caps count uncached tokens (input minus cache reads, plus cache writes and output); cache reads are recorded separately, because a single Codex or Claude session exceeds 50,000 tokens with cache. Frozen criteria: [pilot_acceptance.md](pilot_acceptance.md).

Prompt suffix for every mode:
> Finish this bounded task as quickly as possible. Budget: at most 50,000 tokens across coordinator and subagents, six minutes total, at most one correction after checks. Deliver only the minimum sufficient result and evidence. Do not add optional improvements, deployment, or unrelated repairs. Preserve the supplied task and infrastructure limits. Report incomplete work honestly when the budget ends.

The harness, not the instruction alone, must enforce deadlines and token accounting. JEV requests are authorized separately without a numeric cap, but count requests and available input/output usage per task/mode. Do not retry answers for a preferred result.

Allowed model families: Codex Luna/Terra/Sol 6.1; Claude Opus 5.5/Sonnet 5.5/Haiku; OpenCode OpenAI/dats. Resolve exact available IDs on work, preserve pins, and never infer a capability tier for an unknown model from its name or price.

## Publication

Record acceptance/quality, elapsed time, human correction minutes, retries, escalations, recommended/submitted/observed model evidence and per-agent usage. Total cost per accepted task includes failed attempts and JEV when monetary prices are verified. Separate subscription quota, actual payments and calculated API equivalents; unknown prices mean incomplete cost evidence. A static review cannot demonstrate a production speedup.

Publish anonymized method/results and failures through the existing root README linking here. Three tasks and single-run cells are exploratory, not statistical proof. Current outcome: not run; no efficiency, savings or quality claim has been established.
