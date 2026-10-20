# JEV-EPIC implementation handoff

Status: candidate 1.6.0, ready for human acceptance, not accepted. The Codex preselection defect from the native calculator session is fixed and checked offline and natively (with the limits below). The comparative pilot is NOT RUN. No merge or release publication is authorized.

## Confirmed causes and behavior

The checked upstream main equals audit commit 1805b9a. Shell operands used project root instead of cwd; price sorting assigned OpenCode capability tiers; old task IDs/approval history could survive restart or be restored by late answers; encrypted Codex assignments exited before model selection.

The implementation uses actual cwd or native permission fallback, explicit capability maps, task-generation isolation with locked stale-answer checks, and an open-assignment prepare-spawn interface. Cached allow rechecks path boundaries. Native pins and profile restrictions win. Automatic goal detection and quality-driven model escalation are not implemented.

Codex preselection defect (calculator session), four causes:

1. The response exposed two names (`task_name=jev-<id>` and `spawn.task_name=<role>`). Now `spawn` is the only callable object, and the top-level `task_name` is gone.
2. Policy profiles could not use a unique name, so correlation was unavailable. Now `spawn.agent_type` selects the profile and `task_name` only correlates the launch.
3. Codex rejects `-` in agent names (found natively). The name is now `jev_<hex>`.
4. Correlation evidence was missed. `PostToolUse` delivers the spawn result as a JSON string, and `SubagentStart.agent_id` is a thread UUID. The adapter now parses the string and maps the UUID through the host-supplied transcript's `session_meta`.

A denied ticket is logged as `recommendation_discarded`. The coordinator falls back once to role defaults without retry. Contract: [preselection](preselection.md).

Regression-first evidence: the single-spawn-location, `agent_type` and discard-reporting tests failed before the fix. The name rule and string-response defects were reproduced natively first (run 1 rejection; run 2 unbound record); their tests were added with the fixes.

## Verification

- `make test-jev-hooks`: 183 passed.
- `make lint`: passed.
- `make test`: passed (Rust unit 162, CLI 38, offline e2e 13, content 36, JEV 183, notifier 31).
- Native narrow checks: [facts](native-smoke.json).
  - Codex run 2 applied the recommended `gpt-6-luna` to a `sandbox_mode` developer profile through `agent_type` + `jev_<hex>`. The role default would have been `gpt-6.1-sol`.
  - The record reached `observed` only in a replay of the recorded spawn output after the string-response fix. A fully live chain is still one native run away.
  - Claude Code and OpenCode passed one prompt each. JEV routing and model observation work there, and the prepared flow is not used.

Local traces are in the Git-ignored `.agentic-blackbox/20261020-133533/`. Published facts omit private project names.

## Usage and cutoff

Cutoff: native checks on 2026-10-20, before this documentation commit.

| Agent/run ID | Role | Model | Input | Cached subset | Output | Total | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Claude main session | coordinator | claude-opus-5-5 | not measured | not measured | not measured | not measured | no counter exposed |
| Explore: code | read-only exploration | inherited | not split | not split | not split | 52,496 | subagent report |
| Explore: docs | read-only exploration | inherited | not split | not split | not split | 38,531 | subagent report |
| Codex native checks (3 roots + 2 children) | coordinator / developer | gpt-6.1-sol, gpt-6-luna | 603,471 | 476,032 | 2,189 | 605,660 | rollout token_count |
| Claude Code smoke | coordinator + developer | sonnet, claude-haiku-5-5 | not split | not split | not split | $0.17 session cost | stream-json result |
| OpenCode smoke | coordinator (child not exposed) | openai/gpt-6-luna | 13,661 | not exposed | 124 | partial | step-finish events |
| **Measured total: partial** | | | | | | | incomplete coverage |

JEV separately: 5 calls, input 5,527, output 240 (Codex 3, Claude 1, OpenCode 1). One Codex run was unintended: a process left over from a stalled first attempt. It is counted above. Codex quota before: 5h 11% left, weekly 86% left (user `/status`). Quota after: not yet recorded. No savings or quality claim.

The earlier Codex implementation session's usage was not measured; see Git history of this file.

## Next gate

1. Human acceptance of the implementation and the remaining limits:
   - The fully live `observed` chain is unproven; it was shown only by replay.
   - Sandbox narrowing under a broader parent is unproven.
   - Native per-agent tokens are partial.
2. Then a separate budget request for the 27 primary + 12 ablation runs ([pilot protocol](pilot.md)), with the after-quota shown first.
3. The success Post-task review runs once after acceptance.

## Manual acceptance

From this repository root:

```sh
make test-jev-hooks   # expected: Ran 183 tests ... OK (mocks only, no paid API)
make lint             # expected: exit 0
make test             # expected: exit 0
python3 -m json.tool docs/jev-integration/epic/native-smoke.json >/dev/null && echo valid   # expected: valid
make build && git diff --stat main -- extensions/codex/hooks/jev   # expected: prepared.py, adapters.py, hook.py changed
```

Check the response contract without a paid call (JEV disabled in an empty directory):

```sh
d=$(mktemp -d) && echo '{"settings":{"jev":{"enabled":false}}}' > $d/.agentic.json && \
  echo '{}' | PYTHONDONTWRITEBYTECODE=1 python3 extensions/codex/hooks/jev/hook.py --host codex --project-dir $d --prepare-spawn
# expected: {"status": "fallback", "reason_code": "disabled", "observed_model": null}
```

Read the [preselection contract](preselection.md): `spawn` is the only callable object, `jev_<hex>` names, `recommendation_discarded` on deny. Optional native rerun: the isolated project `/tmp/agentic-jev-blackbox-codex-8lk2ebos` is already trusted. One prompt there proves the live `observed` chain and costs about 200k Codex tokens. Cleanup: remove the `/tmp/agentic-jev-blackbox-*` projects and `.agentic-blackbox/20261020-133533/` after inspection.
