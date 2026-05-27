# Agentic Stabilization v0.3.0

## User-Facing Behavior

- Post-install doctor checks run independently for `codex`, `opencode`, `claude`, and `gemini`.
- `AGENTIC_DOCTOR_TIMEOUT_SECONDS` defaults to `10`; a timeout is reported as a doctor failure and install continues.
- Codex doctor runs non-interactively with `--ephemeral`, `--sandbox workspace-write`, and the same lightweight smoke prompt as other supported doctor targets.
- OpenCode uses an install-time `agent-model-mapper` flow instead of the removed `model-checker` artifacts.
- `agent-model-mapper` writes `.opencode/opencode.json` during interactive install only after confirmation.
- `agent-model-mapper` uses `fzf` for install-time model dropdowns when available.
- No runtime OpenCode plugin is shipped for `agent-model-mapper`, so OpenCode startup never opens `fzf`, asks questions, or writes project files.
- Context7 offers an interactive key mode: configure without a key or enter `CONTEXT7_API_KEY` for the selected target configs.
- OpenCode MemPalace setup writes `mempalace-mcp` config and initializes/mines project memory into a project-specific wing without LLM calls.
- Telegram notification credentials are read from project `.agentic.json` when the plugin is enabled.
- MemPalace-enabled installs create a managed `.mempalaceignore` unless the target project already has one.
- `make test` runs the fast deterministic e2e suite; longer deterministic checks, real blackbox, and coverage checks are explicit targets.
- `make test-all` runs the full local suite including longer deterministic checks, install/evidence blackbox, and coverage.
- Real Codex, OpenCode, and Telegram blackbox install/evidence scenarios run through `make test-real-blackbox`.
- Live Codex/OpenCode/Telegram blackbox sessions require `AGENTIC_REAL_BLACKBOX_LIVE=1`.
- `make test-coverage` traces `agentic` through e2e runs and fails below 90% line coverage.

## Acceptance Criteria

- Hung agent doctor commands time out and do not stop remaining selected agents from running.
- Doctor output includes timeout duration, exit status, and per-agent elapsed time.
- `extensions/opencode/plugins/model-checker.ts` and `model-checker.json` are absent.
- `extensions/opencode/plugins/agent-model-mapper.ts` is absent.
- `extensions/opencode/opencode.json` does not list `agent-model-mapper`.
- Install-time model mapper execution still writes confirmed role model mappings.
- Telegram plugin tests prove environment-only credentials and no secret output.
- Real blackbox tests print created files, managed guidance sources, and MCP config evidence, then save instruction evidence to a temp file without printing Telegram secrets.

## Operational Constraints

- `make test` is deterministic, designed for a sub-minute local loop, and does not require real agent binaries, model auth, network access, Context7/MemPalace access, or Telegram credentials.
- `AGENTIC_REAL_BLACKBOX_LIVE=1 make test-real-blackbox` requires real `codex` and `opencode` binaries, working model auth, network access, Context7/MemPalace access, and Telegram credentials for the Telegram case.
- Telegram credentials must never be committed or written to Agentic config.
- Coverage is line-based Bash trace coverage for the `agentic` script, not branch coverage.
