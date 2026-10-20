# Codex preselection contract (1.6.0)

Use an open assignment before the native transport encrypts it. The coordinator receives current session_id/task_id in workflow hook context, chooses a unique request_id for each logical launch, and sends JSON stdin to:

```sh
python3 .agent/jev/hook.py --host codex --project-dir . --prepare-spawn
```

Example input (replace identifiers with the current task's values):
```json
{"session_id":"current-session","task_id":"current-task","request_id":"unique-launch-id","role":"developer","goal":"Implement four arithmetic operations","scope":"One CLI module, no deployment","complexity":"Established arithmetic pattern; validate input and division by zero"}
```

## Response: one authoritative spawn location

The response reports decision_id, role, recommended_model, model_source, expiry, submitted_model/observed_model (initially null), application_status and correlation_status. These fields are evidence, not spawn arguments. Only a `spawn` object is callable, and it appears only while a safe candidate exists:

```json
{"spawn": {"agent_type": "developer", "task_name": "jev_<32 hex>", "model": "gpt-6-luna", "fork_turns": "none"},
 "on_reject": "native_default_report"}
```

Copy every field of `spawn` unchanged into the native V2 `spawn_agent` call and add only the complete assignment as `message`. Do not copy decision_id or any other response field. The initial recommendation is not execution evidence.

- `agent_type` selects the canonical role profile. Its sandbox, instructions, reasoning effort and model pin stay in force.
- `task_name` names the registry record only. Codex accepts agent names with lowercase letters, digits and underscores, so the name is `jev_<hex>`.
- `model` is absent when the role profile pins a model. Codex then reports "This role's model is set to X and cannot be changed", and the pin applies natively.
- `fork_turns=none` because full-history forks reject model overrides.

Preparation uses the same model question, threshold, listed profile/tier pool, availability cooldown and fallback as spawn hooks. Low confidence/API failure can return the eligible role default tagged model_source=role_default. Disabled/session-off/missing metadata makes no paid request. User profile model pins win. Request retries return the recorded answer; conflicts, expired or consumed decisions never initiate a new paid call.

## Rejection: explicit fallback, no retry

`PreToolUse` denies a prepared launch when the ticket is expired, reused, from another task generation, has a changed profile pin or policy, a different `agent_type`, a different model, or a full-history fork. The denial reason contains the reason code and `recommendation_discarded`. The coordinator then spawns once with native role defaults (`agent_type` only, no model), does not retry the ticket or prepare again for that launch, and reports the reason code. The event log records the denied launch with outcome `recommendation_discarded`, so a silent substitution cannot look like an applied recommendation.

## Correlation

1. Claim binds the actual `tool_use_id` to one record and checks task generation, `agent_type`, model, fork, candidate availability and unchanged profile pin/policy. Status: `submitted_unconfirmed` / `submission_bound`.
2. `PostToolUse` binds the native spawn result. Codex 0.163.0 returns it as the JSON string `{"task_name":"/root/jev_<hex>"}`. A host error string never binds.
3. `SubagentStart.agent_id` is a thread UUID, not a path. The adapter reads only the first line (`session_meta`) of the host-supplied `transcript_path`. The line is accepted only when its `id` equals that `agent_id`; its `agent_path` then gives the canonical child path. A parent or foreign transcript, a missing file or a mismatch keeps the observation unbound.
4. An observation that arrives before the spawn result stays pending until the exact child/tool binding arrives. Then the record becomes `observed` / `native_child_bound`. Conflicts become `observation_conflict`.

Two assignments of the same role never borrow each other's decisions. There is no last-decision, role-only or time-proximity join. Missing evidence stays unconfirmed.

## Native evidence (Codex 0.163.0, 2026-10-20)

- Local coordinator logs show 15 `spawn_agent` calls with `agent_type` separate from `task_name`. The binary embeds the hook input schema with `agent_id`/`agent_type` and the "cannot be changed" text for pinned role models.
- Narrow run 1 (old `jev-` name): the host rejected the name ("agent_name must use only lowercase letters, digits, and underscores"). The coordinator made one role-default fallback and reported `recommendation_discarded`.
- Narrow run 2 (`jev_` name, developer profile with `sandbox_mode`): the host accepted `agent_type=developer`, `task_name=jev_<hex>`, `model=gpt-6-luna`. The child session recorded `agent_role=developer`, `agent_path=/root/jev_<hex>`, model `gpt-6-luna`; the role default would have been `gpt-6.1-sol`. The record stayed `submitted_unconfirmed` because the adapter accepted only dict spawn responses. After the string-response fix, replaying that recorded spawn output in the same project produced `observed` and passed the blackbox application check. The `PostToolUse` string shape is inferred from the recorded tool output; confirm it on the next native run.
- Sandbox inheritance: the top-level run used `danger-full-access` because this host blocks bwrap. The child also reported `danger-full-access`, so this run does not prove that the profile's `workspace-write` narrows a broader parent. The run 1 fallback child with the canonical name `developer` reported the same `danger-full-access`, so the result does not depend on the naming form. JEV does not change sandbox policy either way.

Facts and quota: [native-smoke.json](native-smoke.json).

## Safety and rollout

No decryption, hidden session inspection, permission grants or profile rewriting. The adapter reads only the transcript path the host passes to the hook, and only its first line. Valid prepared PreToolUse records submission and returns no input/approval override. Without prepared metadata, encrypted spawns keep the existing role-default fallback.

Run agentic upgrade with the candidate build to install the updated runtime and coordinator context. No new hook trust bypass is introduced. Native hooks still require the user's existing trust review. Use jev on to begin a new task; old prepared records cannot cross its generation. Claude Code and OpenCode have no prepared flow and keep their existing adapters.

Official contracts checked 2026-10-20: [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), [hooks](https://learn.chatgpt.com/docs/hooks). Local CLI: 0.163.0.
