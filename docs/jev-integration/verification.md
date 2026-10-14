# Native verification, 2026-10-14

## Scope and outcomes

Real installed Codex and OpenCode V2 received the exact prompt
`разработай калькулятор` in separate temporary Git projects created by Agentic.
Installation selected `software.backend` and `software.general` with JEV enabled.
OpenCode tests used only OpenAI models. Codex hooks were reviewed and trusted in
the native TUI; no sandbox or hook-trust bypass was used.

Both environments selected and loaded `development-cycle-workflow`. Native
observations confirmed model application, and independent probes executed the
delivered calculator APIs for addition, subtraction, multiplication, division
and division by zero. Agent-authored acceptance JSON was not used as proof.

| Environment | Confirmed routing | Evidence limits |
| --- | --- | --- |
| Codex 0.161.0 | Real JEV decisions applied `gpt-6-luna` to developer and QA in the initial run; developer and memory curator in the subsequent verification | Other assignments fell back below confidence 0.9. Exact encrypted assignments remained unavailable. |
| OpenCode V2 | Real JEV decisions applied `openai/gpt-5.5-fast` through native `subagent.model` | Catalog prices were unknown. Some other events retained native models; this is not proof of savings for every role. |

OpenCode routing uses production rules, without a special test routing override.
Candidates come from installed role defaults and the available host catalog.
Explicit tool/Markdown/local configuration pins remain authoritative.

Recorded JEV costs for representative runs were $0.003619 for Codex and
$0.004826 for OpenCode. These are decision-service costs reported by the gateway,
not coding-model costs or measured savings. The shared conservative budget ledger
remained below the agreed $5. No official paid quota was used; official API
contracts were checked offline.

Local cleansed artifacts are under `.agentic-blackbox/20261014-113837/` for Codex
and `.agentic-blackbox/20261014-120201/` for OpenCode. They are ignored and are not
part of a clone. `project.json` identifies each retained temporary project.
Subsequent verification uses only the session in its current native trace;
previous successful sessions cannot pass a new failed run.

## Review handoff

The Codex verification confirmed that instruction reviewer consumed the current
task's JEV decision records and returned concrete followups with source, target,
owner and completion criteria. Encrypted assignments were preserved byte for byte;
the journal path was delivered through native `SubagentStart` context.

OpenCode receives a task-scoped packet directly in its reviewer assignment, with
an absolute path to the full packet and referenced records. Inline context is
bounded to 64 KiB. This avoids relying on ordinary search, which skips ignored
journals, or on coordinator claims that the records are absent. Recommendations
are advisory and do not authorize edits to instructions or exceptions to customer
approval requirements.

Browser interaction and external release were not independently demonstrated.
The acceptance probe verifies calculator arithmetic, not screenshots, viewport
layout, deployment or a merged PR in the temporary projects.

## Offline checks

All checks run through Makefile targets. Unit/CLI/content/hook tests cover native
contracts, default model pools, pins, low confidence, timeout/failure, disabled
integration, redaction, retention, event deduplication, permission boundaries,
foreign hooks, edited assets and migration. SDK typechecking uses pinned OpenCode
2.0.28. Rust coverage passed the 80% line gate (82.83%).

Permission checks include outside paths, secret files, deletion, patch move
destinations, symlink escapes, shell working directories and indirect shell file
reads. Independent calculator probes reject broken arithmetic and self-reported
acceptance. A run lock prevents overlapping tests from corrupting a shared trace.
