# JEV-EPIC architecture and risks

Keep network/client logic in api.py and routing in routing.py. The local prepare-spawn interface reuses run_event, model_request, thresholds, catalog and role fallback. It does not decrypt transport data.

Prepared records bind project (directory), host, session, task generation, request ID, canonical role and scrubbed assignment fingerprint. Atomic writes and per-record locks make request retries idempotent; a claimed tool-use ID cannot be consumed by another launch. Expiry is ten minutes. The prepare response has one callable `spawn` object: `agent_type` selects the canonical role profile, and the `jev_<hex>` task name correlates the launch. Task names never select role profiles. Pins win at prepare and claim time; a pinned role gets no model argument.

Native Codex supports explicit model, but full-history forks cannot override it; use fork_turns=none with a complete assignment. Custom profile model takes precedence over spawn model. Sources: https://learn.chatgpt.com/docs/agent-configuration/subagents and https://learn.chatgpt.com/docs/hooks (checked 2026-10-20); local CLI 0.163.0. Codex agent names allow only lowercase letters, digits and underscores. The PostToolUse spawn result is a JSON string with the canonical child path. SubagentStart gives a thread UUID; only the host-supplied transcript whose first-line `session_meta.id` equals that UUID maps it to `agent_path`. Opaque or missing child linkage remains unconfirmed. No role/time/last-decision matching.

Review accounting consumes supplied public/native usage only, never hidden Codex internals. Cached input and reasoning output are subsets, not extra tokens. Unknown coverage means a partial total, never zero cost.

Risks: transport hides task_name; profile overrides model; native model observation absent; catalogs do not prove quota; no confirmed prices means no money claim. Each has a native fallback or explicit evidence limitation. Deployment is skipped: this change is installer/runtime code and documentation, not a production infrastructure rollout.

Late answers and cached decisions must check current task generation under the context lock; an old workflow/permission response cannot undo jev on. Cached allow also rechecks the current path/symlink boundary. Invalid unique prepared tickets are blocked rather than passed as native pins. The coordinator then uses native role defaults once, without retry, and the event log records `recommendation_discarded` with the reason code. Early native observations stay pending until an exact child/tool binding.
