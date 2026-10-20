# Codex preselection contract (1.6.0)

Use an open assignment before the native transport encrypts it. The coordinator receives current session_id/task_id in workflow hook context, chooses a unique request_id for each logical launch, and sends JSON stdin to:

```sh
python3 .agent/jev/hook.py --host codex --project-dir . --prepare-spawn
```

Example input (replace identifiers with the current task's values):
```json
{"session_id":"current-session","task_id":"current-task","request_id":"unique-launch-id","role":"developer","goal":"Implement four arithmetic operations","scope":"One CLI module, no deployment","complexity":"Established arithmetic pattern; validate input and division by zero"}
```

The response contains decision_id, recommended_model, model_source, expiry, submitted_model/observed_model (initially null), and actionable spawn parameters only when a safe candidate exists. Copy only spawn.task_name/model/fork_turns into the supported native V2 spawn schema, and provide the complete assignment in message. Do not pass decision_id as a new spawn argument. The initial recommendation is not execution evidence.

Preparation uses the same model question, threshold, listed profile/tier pool, availability cooldown and fallback as spawn hooks. Low confidence/API failure can return the eligible role default tagged model_source=role_default. Disabled/session-off/missing metadata makes no paid request. User profile model pins win. Request retries return the recorded answer; conflicts, expired or consumed decisions never initiate a new paid call.

## Profile and correlation limits

Codex custom profile model takes precedence over explicit spawn model. Full-history forks reject model overrides, so returned parameters use fork_turns=none. The coordinator must include the complete task context and load the canonical role's instructions.

Simple profiles can use a unique task_name tied to one atomic registry record for ten minutes. Claim binds the actual tool_use_id, checks the task generation, candidate availability, model, fork and unchanged profile pin. Two assignments of the same role never borrow each other's decisions. PostToolUse can bind native tool_response.task_name; model observation must match that exact child identifier. Early observations are held pending and remain unconfirmed until an exact native PostToolUse child binding arrives. Missing or conflicting observations remain unconfirmed. There is no last-decision or role-only join.

A unique task name may bypass a canonical custom profile's sandbox/capability settings. For any profile with policy keys/sections, including bundled sandbox_mode, preparation returns the canonical role task_name and correlation_status=unavailable_profile_preservation instead. This preserves native profile selection and pins but cannot automatically link the recommendation to a particular encrypted spawn. application_status stays unconfirmed; submitted_model/observed_model remain null in the prepared decision. No claim of confirmed application is allowed. Concurrent canonical-role launches must obey the host's naming restrictions; do not invent unique aliases that bypass the profile.

The encrypted assignment alone does not stop the earlier JEV decision. However this release cannot promise fully confirmed routing for every Codex transport/profile combination. Native observations and counters can be unavailable. Unit mocks prove state handling, not the live host's application.

## Safety and rollout

No decryption, hidden session inspection, permission grants or profile rewriting. Valid prepared PreToolUse records submission and returns no input/approval override. Invalid, expired, reused or changed-profile unique tickets are denied through the existing native PreToolUse contract so stale parameters cannot execute. Launch the canonical native role with its defaults/pins instead; no automatic re-evaluation or permission grant occurs. Native model pins and sandbox policy retain control. Without prepared metadata, encrypted spawns keep the existing role-default fallback.

Run agentic upgrade with the candidate build to install prepared.py and updated coordinator context. No new hook trust bypass is introduced. Native hooks still require the user's existing trust review. Use jev on to begin a new task; old prepared records cannot cross its generation.

Official contracts checked 2026-10-20: [subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), [hooks](https://learn.chatgpt.com/docs/hooks). Available local CLI: 0.161.0. Native smoke evidence and limits are recorded in [delivery summary](delivery_summary.md).
