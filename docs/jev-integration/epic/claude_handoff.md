# JEV-EPIC: continuation handoff for Claude

Updated: 2026-10-20. Workflow: `develop-epic`; coordinator: `product-owner`.
Branch: `codex/JEV-EPIC-integration`. Draft PR: https://github.com/sawrus/agent-guides/pull/76.
Implementation checkpoint before this documentation commit: `c60f3a0e1763afec3b7fb0b378d34d32a07fbe79`.
Do not merge or publish a release. The user has not accepted the implementation.

## Read first

Read root `AGENTS.md`, discover current `.agent/` guidance, and follow the requested workflow. Start with [delivery contract](epic_plan.md), [architecture](architecture_notes.md), [preselection contract](preselection.md), [delivery evidence](delivery_summary.md), and [pilot gate](pilot.md). Keep requirements and behavior docs current with each fix.

## Implemented and verified offline

- Shell arguments resolve from confirmed command cwd. Unknown cwd falls back to native permissions. Symlink, root and secret checks remain active.
- Explicit model capability maps replace price-derived tiers. Overrides, availability and pins remain authoritative.
- Existing `jev on` / `/jev on` starts a new task generation and clears old task/workflow/approval context. Follow-ups retain the current task without another workflow decision.
- Shared-runtime `prepare-spawn` accepts open goal/scope/complexity before encrypted transport. It implements bounded/redacted input, request deduplication, atomic registry records, ten-minute TTL, task binding and one-use claims.
- Model reporting separates recommended, submitted and observed values. Profile restrictions and native pins take priority. Missing correlation is reported as unconfirmed.
- REVIEW_PIPELINE requires per-agent/model usage tables, source/cutoff and partial totals; JEV usage is separate. Synthetic usage fixtures cover cached tokens, cumulative counters, repeated roles and reviewers.
- Installer, coordinator guidance, documentation, changelog and version sources are updated to candidate version `1.6.0`.

Last implementation checks: `make test-jev-hooks` passed 172 tests; `make lint` passed; `make test` passed 452 tests. See delivery evidence for the breakdown and bounded smoke limitations. These results precede the native defect below and do not prove production readiness.

## Confirmed native defect: recommendation lost before spawn

A read-only audit of a user's calculator session reproduced the defect against the current candidate runtime. Installed `hook.py`, `adapters.py`, `routing.py` and `prepared.py` match repository source except generated provenance comments. This is not a stale installation.

The first prepared Product Owner decision recommended `gpt-6-luna`. Its public response exposed two different names:

```json
{
  "task_name": "jev-<unique decision UUID>",
  "role": "product-owner",
  "recommended_model": "gpt-6-luna",
  "correlation_status": "unavailable_profile_preservation",
  "spawn": {
    "task_name": "product-owner",
    "model": "gpt-6-luna",
    "fork_turns": "none"
  }
}
```

The coordinator copied the outer name into native spawn. The hook rejected it with `prepared_correlation_unavailable`: the canonical custom profile contains policy settings, so a unique alias cannot safely replace it. The coordinator then retried with an unrelated task name and omitted `model`. The encrypted assignment took the ordinary `assignment_unavailable` path; the role default and native observed model were `gpt-6.1-sol`.

All seven prepared records in this session retain `submitted_model=null`, `observed_model=null`, and `application_status=unconfirmed`. Subsequent ordinary spawns did not establish a link to those records. PM and QA happened to use `gpt-6-luna`, but matching model names do not prove application of their recommendations. Team Lead and Developer had low-confidence prepared decisions and correctly fell back to their role defaults; that threshold behavior is not itself a defect.

Workflow selection worked: `development-cycle-workflow`, confidence 0.96, applied. Ordinary follow-ups did not request another workflow decision. The runtime recorded seven JEV requests with 7,284 input and 423 output tokens. This is a separate user session, not the earlier bounded smoke's three calls. Do not combine either count with native agent usage, which was not measured. No new paid calls were made during this audit.

Raw session identifiers, internal paths and full task transcripts are deliberately not published here. The local project retains `.agentic/jev/event-*.json`, `prepared-*.json`, and `.reviews/<task-id>/summary.md` plus `instruction-review.md`. Inspect only permitted native/app evidence and these explicit runtime logs; do not decrypt assignments or inspect hidden host internals.

## What Claude must complete

1. Add a failing synthetic regression for the actual profile-preservation response and coordinator-to-native parameter contract. The current offline tests missed that conflicting public names caused the recommendation to be discarded.
2. Make the public response and coordinator instructions unambiguous: native spawn parameters must have one authoritative location. Separate registry identity from callable native parameters. A recommendation must not be silently replaced after a failed attempt. Preserve native pins and profile restrictions.
3. Recheck the actual host schema before choosing a correlation mechanism. Observed hook inputs can contain `agent_type` separately from `task_name`, but that does not prove the caller may supply `agent_type`. App events expose native thread IDs and canonical paths; native SubagentStart IDs can be UUIDs. The current path-based binding assumptions require explicit native verification. Do not invent API fields or join by role, time proximity or latest decision.
4. Keep unavailable correlation honestly unconfirmed. Never bypass a canonical profile's sandbox/policy just to obtain a unique name. Check profile model precedence before claiming an explicit model was applied.
5. Cover encrypted assignments, parallel same-role launches, retry deduplication, expiration/reuse, task restart, pin/profile changes, low confidence, timeout, unavailable models and absent correlation. Preserve Claude Code and OpenCode behavior.
6. Run `make test-jev-hooks`, applicable lint, and `make test`. Use mocks and synthetic files first. Narrow native blackbox checks are authorized, but record their quota usage and limitations. Do not retry repeatedly to manufacture a passing outcome.
7. Update this handoff, preselection contract, delivery evidence, changelog and draft PR with the final mechanism, remaining limits and actual checks. Keep version sources synchronized; the branch already targets 1.6.0.

Calculator delivery also lacked runtime verification and its QA report said no-go for release. This is separate from proving JEV model application. Do not count that task as an accepted benchmark or infer quality/cost savings from the files merely existing. Post-task reviewers already ran inside that calculator session; they are not evidence that this epic received human acceptance.

## Not implemented or not established

- The newly confirmed native defect has been investigated and documented, not fixed.
- Fully correlated model application across the installed Codex policy profiles is not proven. Mocks are not native evidence.
- Native per-agent token totals, monetary costs, savings and quality improvements are not measured.
- Automatic goal-change classification and quality-driven model escalation remain out of scope.
- The 27 primary + 12 ablation comparative runs have not started. No efficiency results are published.
- Human acceptance, the epic's successful-delivery post-task review, merge and release remain pending.

## Mandatory budget stop

Complete the implementation and present reviewable evidence first. Obtain explicit implementation acceptance, then separately ask permission to spend budget on the comparative matrix. Acceptance alone is not budget authorization. Before that request, show measured spend and remaining quota where available; unknown values must remain unknown.

The approved pilot has three hosts and three modes (no agentic, fixed workflow without JEV, workflow with JEV), plus separate workflow/model ablations. Each run is bounded by 50,000 tokens and six minutes, with at most one repair inside the budget. Each host has an aggregate one-million-token cap covering blackbox, agents, retries and repairs. JEV requests are counted separately. Follow the full [pilot protocol](pilot.md), including isolated copies, controlled `agentic upgrade`, independent acceptance criteria and anonymized publication. Do not start it during this handoff.
