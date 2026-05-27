# Changelog

## v0.3.3

- Updated MemPalace project initialization to pipe explicit confirmation (`echo "Y" | mempalace init ...`) for non-interactive setup robustness.
- Removed `agent-model-mapper` from OpenCode plugin registration.
- Deleted obsolete OpenCode plugin source `extensions/opencode/plugins/agent-model-mapper.ts`.

## v0.3.2

- Added optional post-task specialist agents `instruction_reviewer` and `memory_curator` outside the mandatory SDLC role matrix.
- Added review pipeline guidance, `.reviews/<task-id>/` output conventions, and documented example instruction/memory review reports.
- Registered the new specialists in OpenCode role configuration and extended deterministic install/model-mapper coverage.

## v0.3.1

- Added project-level OpenCode plugin settings in `.agentic.json`, including Telegram `botToken` and `chatId` when `telegram-notification` is enabled.
- Renamed the OpenCode optional plugin menu entry to `telegram-notification` while preserving the old `telegram-opencode-notifier` alias for compatibility.
- Changed `telegram-notification` runtime credentials to read from the target project's `.agentic.json` instead of Telegram environment variables.
- Removed Telegram message formatting entirely: notifications are sent as plain text without `parse_mode`, MarkdownV2 escaping, or markdown-to-Telegram conversion.
- Added interactive Context7 key mode selection with English menu entries for keyless setup or entering `CONTEXT7_API_KEY`.
- Removed the post-install Context7 "add API key later" path/example guidance because key selection now happens during setup.
- Extended `agent-model-mapper` model discovery to include active providers from `~/.local/share/opencode/auth.json` and non-deprecated models from `~/.cache/opencode/models.json`.
- Added a Confirm/Cancel save step after OpenCode role model selection before writing `.opencode/opencode.json`.
- Preserved OpenCode plugin settings across manifest replay/re-install so automated sync does not prompt again or lose project-level credentials.
- Updated OpenCode, Context7, Telegram, and lifecycle docs plus deterministic e2e coverage for the new configuration flow.

## v0.3.0

- Added per-agent doctor timeouts with elapsed-time and exit-status logging while keeping install non-fatal.
- Replaced the OpenCode model checker with `agent-model-mapper` for explicit role-to-model mapping.
- Moved `agent-model-mapper` prompts to install time so OpenCode startup stays non-blocking.
- Removed the interactive Context7 API-key prompt and made OpenCode MemPalace project initialization optional/manual.
- Changed Telegram notifications to read credentials from environment variables only and avoid logging secrets.
- Added traced shell coverage tooling with a 90% `agentic` line coverage gate.
- Added deterministic OpenCode plugin, Telegram, and doctor timeout continuation tests.
- Added real Codex, OpenCode, and Telegram blackbox scenarios to normal `make test`.

## v0.2.0

- Added `agentic --version` and version display in CLI/TUI output.
- Added post-install doctor smoke checks for selected real agent targets.
- Added timestamped install logging with a mirrored `/tmp/agentic-*` file.
- Added install/TUI runtime requirements checks for Python, pip, and managed-file hashing tools.
- Changed generated MemPalace MCP configs to call `mempalace-mcp` without arguments.
- Added opt-in real-agent doctor E2E coverage.
- Added version metadata for generated Agentic markers while preserving the GitHub repository link.
- Kept schema-sensitive agent configuration files free of Agentic marker metadata.
