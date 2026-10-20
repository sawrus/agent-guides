# JEV-EPIC: continuation handoff

Updated: 2026-10-20 by Claude (continuing the Codex handoff). Workflow: `develop-epic`; coordinator: `product-owner`.
Branch: `codex/JEV-EPIC-integration`. Draft PR: https://github.com/sawrus/agent-guides/pull/76.
Do not merge or publish a release. The user has not accepted the implementation.

## Read first

Root `AGENTS.md`, then [delivery contract](epic_plan.md), [architecture](architecture_notes.md), [preselection contract](preselection.md), [delivery evidence](delivery_summary.md), [native facts](native-smoke.json) and [pilot gate](pilot.md).

## Implemented earlier (Codex) and still valid

- Shell arguments resolve from confirmed command cwd; unknown cwd falls back to native permissions.
- Explicit model capability maps replace price-derived tiers.
- `jev on` / `/jev on` starts a new task generation.
- Shared-runtime `prepare-spawn` with bounded/redacted input, request deduplication, atomic records, ten-minute TTL, task binding and one-use claims.
- Model reporting separates recommended, submitted and observed values.
- REVIEW_PIPELINE per-agent/model usage tables; JEV usage separate.
- Version sources and changelog target candidate `1.6.0`.

## Fixed in this continuation: recommendation lost before spawn

The calculator session had a policy-profile Product Owner. Its recommended `gpt-6-luna` was replaced by the role default `gpt-6.1-sol`. Causes and fixes:

| Cause | Fix |
| --- | --- |
| Response had a top-level `task_name=jev-<id>` and a different `spawn.task_name=<role>`; the coordinator copied the wrong one. | `spawn` is the only callable object; top-level `task_name` removed; `on_reject=native_default_report` added. |
| Policy profiles (`sandbox_mode`, `developer_instructions`) could not use a unique name, so correlation was "unavailable". | `spawn.agent_type=<role>` selects the canonical profile. Local logs show coordinators already pass `agent_type` separately from `task_name`. `task_name` only correlates. |
| After the deny, the coordinator retried without `model`; the substitution was silent. | Deny reason and coordinator guidance: fall back once to role defaults, no retry, report `recommendation_discarded` with the reason code. The event outcome is `recommendation_discarded`. |
| Found natively: Codex rejects `-` in agent names. | Name is `jev_<hex>`. |
| Found natively: `PostToolUse` spawn result is a JSON string; `SubagentStart.agent_id` is a thread UUID. | Adapter parses the string. It maps the UUID to `agent_path` only through the host-supplied transcript whose first-line `session_meta.id` equals that UUID. |

Pinned roles get no `model` in `spawn` because Codex says pinned role models "cannot be changed". Claude Code and OpenCode code paths are unchanged.

Checks: `make test-jev-hooks` 183 OK, `make lint` OK, `make test` OK. Native narrow checks: one prompt per run, details in [native facts](native-smoke.json).
- Codex run 1 reproduced the name rejection. The coordinator correctly fell back once and reported the discard.
- Codex run 2 applied `gpt-6-luna` to the `sandbox_mode` developer through `agent_type` + `jev_<hex>`.
- Claude Code and OpenCode passed.

One Codex run was unintended: a process left over from a stalled first attempt. It is counted in quota.

Live proof (run 4): recommended = submitted = observed = `gpt-6-luna`, `native_child_bound`, without replay. Run 3 found one more defect (list-valued `scope`), fixed with tests. The user conditioned implementation acceptance on this live proof; it passed.

Comparative pilot: all 39 cells ran with the user's budget permission. Results and deviations: [pilot results](pilot_results.md).

Open work with owners and done-when conditions: [tech debt](tech_debt.md). All measurements: [measurements/](measurements/).

## Not established

- Whether a profile's `workspace-write` narrows a broader parent sandbox. Both children reported the parent's `danger-full-access`, independent of naming. JEV does not change sandbox policy.
- Native per-agent token totals are partial; no money, savings or quality claims.
- Automatic goal-change classification and quality-driven escalation remain out of scope.
- Human quality review of pilot outputs, the success Post-task review, merge and release are pending.
- Follow-ups: shrink always-loaded context and re-measure; the installer writes an empty legacy `model` for OpenCode agents.

## Mandatory budget stop

Obtain explicit implementation acceptance first, then separately ask permission to spend budget on the comparative matrix. Acceptance alone is not budget authorization. Before that request, show measured spend and remaining quota. Codex before the checks was 5h 11% / weekly 86% left; the after-value is still to be recorded. The pilot protocol is unchanged: three hosts × three modes plus ablations, 50,000 tokens and six minutes per run, one-million-token cap per host, isolated copies, frozen acceptance criteria, anonymized publication.
