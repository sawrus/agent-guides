# JEV-EPIC architecture and risks

Keep network/client logic in api.py and routing in routing.py. The local prepare-spawn interface reuses run_event, model_request, thresholds, catalog and role fallback. It does not decrypt transport data.

Prepared records bind project (directory), host, session, task generation, request ID, canonical role and scrubbed assignment fingerprint. Atomic writes and per-record locks make request retries idempotent; a claimed tool-use ID cannot be consumed by another launch. Expiry is ten minutes. Task names correlate launches, never select role profiles. Pins win at prepare and claim time.

Native Codex supports explicit model, but full-history forks cannot override it; use fork_turns=none with a complete assignment. Custom profile model takes precedence over spawn model. Sources: https://learn.chatgpt.com/docs/agent-configuration/subagents and https://learn.chatgpt.com/docs/hooks (checked 2026-10-20); local CLI 0.161.0. Hook schemas document tool_use_id/tool_input and PostToolUse tool_response, but opaque or missing child linkage must remain unconfirmed. No role/time/last-decision matching.

Review accounting consumes supplied public/native usage only, never hidden Codex internals. Cached input and reasoning output are subsets, not extra tokens. Unknown coverage means a partial total, never zero cost.

Risks: transport hides task_name; profile overrides model; native model observation absent; catalogs do not prove quota; no confirmed prices means no money claim. Each has a native fallback or explicit evidence limitation. Deployment is skipped: this change is installer/runtime code and documentation, not a production infrastructure rollout.

Late answers and cached decisions must check current task generation under the context lock; an old workflow/permission response cannot undo jev on. Cached allow also rechecks the current path/symlink boundary. Invalid unique prepared tickets are blocked rather than passed as native pins; canonical-profile fallback preserves policy and remains unconfirmed. Early native observations stay pending until an exact child/tool binding.
