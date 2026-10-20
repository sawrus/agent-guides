# JEV-EPIC implementation handoff

Status: draft implementation, not human-accepted. A subsequent native calculator session exposed an unresolved Codex preselection defect; this branch is not production-ready. See the [Claude handoff and native regression evidence](claude_handoff.md). The comparative pilot is NOT RUN. No merge or release publication is authorized.

## Confirmed causes and behavior

The checked upstream main equals audit commit 1805b9a. Shell operands used project root instead of cwd; price sorting assigned OpenCode capability tiers; old task IDs/approval history could survive restart or be restored by late answers; encrypted Codex assignments exited before model selection.

The implementation uses actual cwd or native permission fallback, explicit capability maps, task-generation isolation with locked stale-answer checks, and an open-assignment prepare-spawn interface. Cached allow rechecks path boundaries. Native pins and profile restrictions win. Invalid unique tickets are denied, never silently executed with stale model/profile parameters. Restricted profiles keep canonical native names and unconfirmed application. Automatic goal detection and quality-driven model escalation are not implemented.

Regression-first evidence: new cwd/task tests, capability tests, prepared-interface tests, late-answer race tests, cached-symlink mutation test, stale-ticket adapter tests, usage fixtures and a blackbox regression rejecting role/model-only Codex evidence all failed before their fixes. Verification is through Makefile targets only.

## Verification

- `make test-jev-hooks`: 172 passed.
- `make lint`: passed (rustfmt and clippy were obtained in a temporary directory; no system installation).
- `make test`: 452 passed: Rust unit 162, CLI 38, offline e2e 13, content 36, JEV 172, notifier 31. Offline fake HTTP tests required loopback access outside the execution sandbox. A notifier ResourceWarning did not fail tests.
- Native smoke: see [sanitized facts](native-smoke.json). Codex blocked on missing hook execution/trust, OpenCode official-endpoint fallback verified a calculator without JEV, explicit gateway made three real JEV calls but delivery hit the 90-second bound. Claude CLI is absent. No end-to-end native JEV acceptance or efficiency claim is made.

Local execution logs are under /tmp/jev-epic-*.log; smoke projects/traces remain local and ignored by Git. Published facts omit private project names/paths. The 27+12 pilot has not accessed the target production repositories.

## Usage and cutoff

Cutoff: implementation checks and the bounded smoke runs on 2026-10-20, before the final handoff response. The current agent tools expose no per-agent usage counters. Missing values are not zero; the final response is outside the cutoff.

| Agent/run ID | Role | Model | Input | Cached subset | Output | Total | Source |
| --- | --- | --- | --- | --- | --- | --- | --- |
| /root | product-owner / coordinator | not measured | not measured | not measured | not measured | not measured | no native usage exposed |
| repository_exploration | product-owner, planning review | not measured | not measured | not measured | not measured | not measured | no native usage exposed |
| explore_current | product-owner / team-lead / qa, separate turns | not measured | not measured | not measured | not measured | not measured | no native usage exposed |
| capability_routing | developer | not measured | not measured | not measured | not measured | not measured | no native usage exposed |
| prepared_spawn | developer, repeated turns | not measured | not measured | not measured | not measured | not measured | no native usage exposed |
| review_accounting | developer | not measured | not measured | not measured | not measured | not measured | no native usage exposed |
| **Measured total: partial, unavailable** | | | not measured | not measured | not measured | not measured | incomplete coverage |

Distinct model rows cannot be reconstructed without native model/turn telemetry. No cumulative totals or overlapping turn counters were guessed. Post-task instruction-reviewer and memory-curator are not run yet: the explicit human acceptance gate is pending; the role-based architecture/QA checks above are not impersonated as those specialist reports.

JEV separately: three gateway calls with returned usage, input 3,662, output 231, total 3,893; source is the smoke runtime's response usage records. The other two smoke attempts recorded zero JEV calls. Complete native coding-agent tokens and monetary prices are not measured. No remaining-quota number is invented. Check remaining quota before any later pilot permission request.

## Next gate

First fix and verify the native preselection defect described in the [handoff](claude_handoff.md). Then obtain the user's acceptance of the implementation and its remaining native limitations. Only then ask separately whether to spend the remaining budget on the 27 primary + 12 ablation runs. The pilot protocol is [here](pilot.md). The success Post-task review runs once after acceptance; do not launch it now or recurse on these notes.

## Manual acceptance

From this repository root, run:

```sh
make test-jev-hooks  # expected: 172 tests, OK; mocks/synthetic fixtures, no paid API
make lint            # expected: exit 0; requires rustfmt/clippy
make test            # expected: exit 0; offline fake HTTP requires loopback sockets
```

These commands were run. They do not invoke the comparative pilot. Read [preselection contract](preselection.md), [pilot gate](pilot.md) and the native smoke limitations above. Confirm that invalid prepared tickets cannot bypass changed profiles and that unmeasured usage remains unknown.

Optional native smoke commands are documented in the main JEV README; they consume quota and retain native trust requirements. Codex requires reviewing the installed definitions through `/hooks` before rerunning; this trust step was not performed here. Do not bypass trust or sandbox. Cleanup: remove only the disposable smoke project/run directory you selected after inspecting it. No target production repository or database needs rollback.
