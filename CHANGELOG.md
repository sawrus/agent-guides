# Changelog

## v1.0.0

- Persisted Context7 API-key mode in project manifests so upgrades do not repeat interactive prompts.
- Applied a 30-second default timeout to MemPalace operations, including upgrade graph refresh.
- Removed the obsolete `--install-fzf` option and its report output.
- Fixed the bootstrap installer cleanup trap so successful installs exit with status 0 under Bash `set -u`.

## v0.7.0

- Rewrote the `agentic` CLI from Bash (5598 lines) to Rust: a single self-contained cross-platform binary with the knowledge base (`areas/`, `extensions/`, root guidance files) embedded at build time.
- Removed all runtime dependencies: `git`, `curl`, `jq`, `python3` (for core flows), `fzf`, `sed`/`awk`, and `shasum` are no longer required. `python3`/`pip` are checked only when the optional MemPalace integration is enabled.
- Replaced the fzf-based TUI with a fullscreen ratatui wizard preserving the exact linear flow: theme → project directory → agent OS multi-select → MCP servers (with `[x]` detection of already-configured servers) → areas → per-area specializations → install.
- `agentic upgrade` now downloads the latest release binary from GitHub Releases and atomically self-replaces, then re-syncs the managed project in the current directory (replay install + MemPalace graph refresh).
- New `install` bootstrap script downloads platform binaries (linux x86_64/aarch64 musl, macOS Intel/ARM) from GitHub Releases; Windows x86_64 binaries are published as zip assets.
- Preserved 100% of the install pipeline semantics: manifest idempotency, managed-file protection (unmanaged/user-modified/config skips), marker injection with `created_by` preservation, MCP registry and per-agent config writers, OpenCode plugins/profiles/agent-model-mapper, codex TOML editing, doctor smoke checks with fatal-pattern classification.
- Fixed an upstream validation bug: the documented `default` agent OS is now accepted by `--agent-os` validation.
- Reworked the npm distribution: `@jetrabbits/agentic` is now a thin Node launcher that downloads the platform binary for the matching release tag from GitHub Releases on first run (per-version cache in `~/.cache/agentic-npm/`); publishing runs on GitHub Release publication with a Cargo/npm/tag version-sync gate. Removed the bash e2e suite; testing is now `cargo test` (unit + integration + real-run blackbox e2e with fake agent binaries) with an enforced 80% line-coverage gate (`make test-coverage`).
- Added CI (`ci.yml`: fmt/clippy/tests on linux+macos+windows + coverage gate) and release automation (`release.yml`: 5-target build matrix publishing `agentic-<arch>-<os>` assets with SHA256SUMS).

## v0.6.3

- Added a top-level `agent` field to every workflow frontmatter, matching `execution.initiator`, and updated the workflow template to preserve the contract for newly created workflows.

## v0.6.2

- Simplified the static docs site header by removing the install command block and shortened sidebar workflow labels by dropping the leading slash from triggers.

## v0.6.1

- Improved the static docs site navigation with compact expandable devops/software sections, nested area menus, active workflow state, independent sidebar/content scrolling, and a full-width search field under the install command.

## v0.6.0

- Added area-level `AGENTS.md` indices for `areas/devops/` and `areas/software/` with spec selection, cross-cutting constraints, and a global workflow trigger registry.
- Renamed colliding workflow triggers: full-stack `/develop-feature` → `/develop-feature-fullstack`, full-stack `/debug-issue` → `/debug-issue-fullstack`, platform `/incident-response` → `/service-incident` (devops/sre keeps `/incident-response`; backend keeps `/develop-feature` and `/debug-issue`). Update any saved prompts that used the old full-stack/platform commands.
- Extended the workflow template contract: `devops-engineer` is now a standard role; every loop/retry must state a maximum iteration count and an escalation path; cross-workflow trigger chains must be acyclic or carry a circuit breaker; every workflow Exit ends with an explicit `Next: /trigger` or `Next: terminal` handoff.
- Bounded all previously unbounded fix/retest, review, and mitigation loops across devops and software workflows, and added circuit breakers to the backup-verify ↔ db-incident, crash-triage ↔ store-submission, smoke-test ↔ deploy-production, and mlops incident→retrain→redeploy cycles.
- Added the missing rollback failure path to `/secret-rotation` (previous credential retained until the new one is verified).
- Standardized completion contracts: delivery workflows end with docs + CHANGELOG + version updates; incident workflows file root causes at `docs/incidents/<date>-<slug>-root-cause.md` (replacing wiki/ticket/`.data`/`.mlops`/`.security` destinations).
- Normalized workflow role hygiene repo-wide: initiators declared in their own roles list, no undeclared or unused step roles, no parenthetical role annotations, and named handoff artifacts in step Inputs.
- Regenerated workflow diagrams, the docs site catalog, and area quality reports (net −102 quality warnings).

## v0.5.3
- Isolated install-time OpenCode doctor runs into a temporary XDG home so doctor no longer reuses or pollutes the user's persistent OpenCode session database.
- Extended doctor e2e coverage to assert isolated OpenCode HOME/XDG paths and prevent `opencode.db` leaks into the caller home.

## v0.5.2
- Updated Codex MCP config generation so selected network-backed MCPs enable project sandbox network access, use non-interactive `npx -y` startup, and include startup/tool timeouts for reliable first-run startup.
- Extended deterministic MCP and doctor e2e coverage for all selected Codex MCP entries.

## v0.5.1
- Moved OpenCode Telegram notification credentials to `$HOME/.config/agentic/config.json` and added interactive reuse of saved credentials.
- Kept project `.agentic.json` limited to Telegram enablement so project manifests no longer store raw Telegram secrets.

## v0.5.0
- Fixed skill and rule dependencies within workflows

## v0.4.0

- Fixed OpenCode MCP config generation to use top-level `mcp` entries and migrate/remove legacy `mcpServers` from generated OpenCode configs.
- Added readable OpenCode menu labels for Telegram notifications and agent model mapping while preserving existing internal ids.
- Added committed OpenCode model profiles for OpenAI and GitHub Copilot under `extensions/opencode/profiles`.
- Added OpenCode profile choices to the optional OpenCode menu with manifest persistence and MCP-safe config merging.
- Renamed generated Docker MCP server entries from `MCP_DOCKER` to `docker`.
- Added non-fatal local prerequisite warnings for selected Kubernetes and Docker MCP integrations.
- Removed the macOS bash 3.2 warning and added compatibility handling for older bash empty-array behavior.
- Extended deterministic e2e coverage for all-MCP doctor setup, OpenCode MCP migration, OpenCode profiles, readable menu labels, and bash 3 compatibility.

## v0.3.4

- Enabled Codex project memories by generating `.codex/config.toml` with `[features] memories = true` whenever Codex is selected.

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
