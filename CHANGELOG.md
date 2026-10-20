# Changelog

## v1.6.0

- Shell permission operands resolve from the actual cwd; unknown cwd retains native approval. Preserve secret, symlink and allowed-root boundaries.
- Capability tiers come from explicit maps and candidate-validated overrides, never price rank; unknown costs remain unknown. Pins, provider filters and role-default fallback stay in force.
- Existing `jev on` is an explicit new-task boundary. Task generations isolate cached decisions, approval history, prepared spawns and review packets; late answers cannot restore a reset task. Cached allow rechecks path boundaries.
- Codex gains a local `--prepare-spawn` interface using open goal/scope/complexity before encryption, with idempotent expiring decisions and separate recommended/submitted/observed evidence. The response has one callable `spawn` object (`agent_type`, `jev_<hex>` task name, model unless pinned, `fork_turns=none`), so restricted profiles keep their policy and still correlate. A denied ticket falls back once to native role defaults and is logged as `recommendation_discarded`. Child observations bind through the host transcript of the exact thread. List-valued metadata is joined; wrong types return `prepared_metadata_invalid`. Live native proof: recommended, submitted and observed model matched.
- REVIEW_PIPELINE adds per-agent/model token tables, provenance, partial totals and separate JEV usage; manual acceptance remains last. No savings are inferred.
- Comparative pilot (39 cells, 3 hosts): plain agents were cheapest on small tasks; see docs/jev-integration/epic/pilot_results.md. New tools: `scripts/pilot_jev.py`, `scripts/render_coverage_scorecard.py`, a real-TUI `scripts/generate_how_to_use_agentic_gif.py`.
- README rewritten for a non-specialist audience; technical details moved to docs/agentic-reference.md.
- Candidate release: not yet published. Re-run upgrade to install the updated runtime; coordinators must start a new task after upgrade so the new spawn contract is injected. See docs/jev-integration/epic/.

## v1.5.0

JEV now decides once per session and spends fewer calls; review reports end with manual acceptance commands. Requirements: `docs/jev-integration/session-gate/README.md`.

- JEV session gate (all hosts). Only the first root prompt of a session asks the workflow question. A selected workflow keeps JEV on; `native`, low confidence or an error turns JEV off for the rest of the session (`session_off`); `clarify` asks again on the next prompt. Later prompts make no call and stay bound to the first task (`session_follow_up`), so answers such as «да» or «как отработал JEV» no longer open a new task or move spawns and review packets to it. A later prompt that names a workflow (`/develop-feature`) starts a new task without a call. In an off session, spawns still get the role default without a call.
- Manual switch: `/jev off`, `/jev on`, `/jev status` per session, with no JEV call. Install adds `.claude/commands/jev.md` and `.opencode/commands/jev.md`; in Codex type `jev off` if the TUI rejects the slash command. Claude Code and Codex hooks block the switch prompt, so it costs no model turn; OpenCode answers with one line. `/jev on` restarts workflow selection.
- Model threshold default is now 0.6 (workflow and permission stay 0.9). Below it, the role default from the installed profile applies.
- Claude in an install with Codex: `model-defaults.json` gains `hosts.claude` with the Claude profile roles and tiers. Before, the Codex ids gave Claude no alias, and low-confidence spawns inherited the coordinator's model (often opus).
- Removed fields that were always empty: `usage.cost_usd` (records now keep `input_tokens` and `output_tokens`), observation `requested_model`, and the `AGENTIC_JEV_BUDGET_FILE` ledger that booked a fixed $0.02 guess per call.
- Blackbox: the prompt is «разработай простой калькулятор на Python в одном файле», at most three prompts and 8 minutes per host (was 20 minutes), and a new `follow_up_without_jev_call` check. `results.json` reports `jev_calls`, `jev_input_tokens` and `follow_up_prompts` instead of `jev_reported_cost_usd`.
- Post-task review: `summary.md` and the final response end with a `Manual acceptance` section: copy-paste commands from the project root, the expected result of each, manual steps and cleanup. Commands not run during delivery are marked `not run`.
- Migration: reinstall the target project to get the new runtime, `hosts.claude` and the `jev.md` commands. Hook entries are unchanged, so Codex needs no new `/hooks` review. Remove `AGENTIC_JEV_BUDGET_FILE` from local scripts. Custom `settings.jev.thresholds.model` values are kept; remove them to use the new 0.6 default. Old `context-*.json` files without `jev` count as on.

## v1.4.1

Bug-fix release for 1.4.0. It fixes the JEV questions, which caused most JEV fallbacks, and the Telegram "done" mark.

- JEV questions rework (all hosts). In the reference run only 2 of 11 answers were applied; the questions caused most fallbacks.
  - Workflow question: options come from `type: workflow` files and show description, inputs → outputs, roles and the new `selection.use-when`; the general workflow is marked `GENERAL.`. New options `native` (`fallback/native_request`) and `clarify` (`fallback/clarification_needed`) keep native behaviour. State has the original request, installed areas and a bounded repository snapshot instead of the catalog.
  - Model question: JEV picks a tier (`fast` / `balanced` / `frontier` / `clarify`) for the assignment; the hook maps it to a model (Claude haiku/sonnet/opus, Codex `extensions/codex/model-tiers.json`, OpenCode by catalog price). The session model is no longer sent or used. `clarify`, low confidence, an API error or `no_tier_routing` apply the role default on Codex, OpenCode and Claude (`model_source: role_default`, was `profile_default`).
  - Permission question: asked only for requests inside the automatic boundary; others are not sent to JEV (`not_auto_allow_eligible`, native host decision). State has path and command metadata only (no file content, no full command, no outside path: `[outside project]`, `secret_like`), the requesting role when it is installed, and the last 10 applied decisions.
  - Redaction no longer corrupts identifiers such as `tests_and_review_evidence`, `parts_inventory_service` or `task-ask-me`: token patterns match only at a token start. `ts_` tokens need a digit; `sk-` (including `sk-proj-`, `sk-ant-`) and `jv_live_` tokens need a digit or 20+ characters. GitHub (`ghp_`…), AWS access key ids (`AKIA`…) and Slack (`xox?-`) tokens are now redacted too.
  - Spawn records label agents like observations: an installed role in `agent`, otherwise `agent: null` and `native_agent_type`. `scripts/blackbox_jev.py` pairs spawns and observations by either label, so native helpers such as `Explore` count.
  - Instructions no longer contain test-case wording. Requests are sent as UTF-8; a Cyrillic prompt no longer inflates the 32 KiB budget about six times.
  - New `settings.jev.thresholds.{workflow,model,permission}` (valid range 0.5–1, default 0.9). Reinstall keeps `thresholds`, `lightweight_model` and `tiers`.
  - Audit records gain `decision`, `threshold`, `applied`, `outcome`, and for spawns `tier` and `model_source`. Observations of non-role subagents (for example `Explore`) have `agent: null`.
  - The runtime is split into `hook.py`, `questions.py`, `routing.py`, `adapters.py` and `api.py`; all are installed to `.agent/jev/`. A partial runtime (including a missing `api.py`) falls back with `runtime_incomplete` and writes an identifier-only record.
  - OpenCode model routing now works without catalog prices (OpenAI oauth reports `cost: []`). A shipped tier map, installed as `.agent/jev/opencode-model-tiers.json`, gives `openai/gpt-6-luna` / `openai/gpt-6.1-sol` / `openai/gpt-6-astra`, filtered to the host catalog and to one provider (`cost_source: tier_map`); a role default on a provider without a map entry gets no map tiers. Complete, distinct prices still win (`catalog_price`). The plugin adds the map models to the spawn pool.
  - OpenCode role defaults are resolved in the hook: a profile model in the catalog wins (`role_default_source: profile`); otherwise the role's tier from the map applies (`role_tier`; `balanced` for product-owner, team-lead, developer, devops-engineer; `fast` for qa, analyst, pm and the reviewers). A default install therefore gets a role default for every installed role. Spawn records gain `cost_source` and `role_default_source`.
  - `instruction-reviewer` without prices or a lightweight model gets the `fast` tier (`tier_fast_price_unknown`).
  - Codex: a spawn with an encrypted assignment is no longer sent to JEV; it gets `fallback/assignment_unavailable` and the role default (every such call had answered `clarify`). The Codex `qa` default is now `gpt-6-luna` (`fast`; `gpt-6-terra` is not in the Codex catalog).
  - The OpenCode `openai` profile now uses only catalog ids with the `openai/` prefix: `developer` → `openai/gpt-6.1-sol`, fallbacks `openai/gpt-6-astra`, `small_model` → `openai/gpt-6-luna`. A content test checks shipped ids against frozen host catalogs.
  - `scripts/blackbox_jev.py` resolves `--run-dir` to an absolute path.
- Migration: `.agent/jev/model-defaults.json` is now `{"version": 2, "roles": {...}, "tiers": {...}}`; reinstall rewrites it, and the hook still reads the old flat file (roles only, no tier routing). Every `areas/**/workflows/*.md` needs a `selection` block (`make lint-content` enforces it); see `CONTRIBUTING.md`. Old `event-*.json` records stay valid; new records use a versioned identity, so an event is not served from a pre-rework record.
- Operational (OpenCode JEV): reinstall to get `.agent/jev/opencode-model-tiers.json`; without it the hook keeps the price-only behaviour. Users with a custom OpenCode profile keep their explicit catalog models as role defaults; a profile model that is not in the catalog is replaced by the role's tier model. Restart OpenCode after the reinstall: the plugin reads the tier map once, at setup.
- Telegram header (all hosts): a second line `🤖 <agent> · <model>` names the main-session agent and the model of the last answer, from local host data. `✅ Задача завершена` is now sent once, on the final turn: the coordinator's turns that leave subagents or background tasks running become `💬 Промежуточный ответ`. When the evidence is unclear, the turn is interim. The new helper `.agent/notify/telegram_turn.py` is installed and removed with `telegram.py`; reinstall to get it (without it, every message is interim). The transcript scan runs only in the detached sender. See `docs/notifications`.

## v1.4.0

- Claude Code now matches OpenCode and Codex. Install writes `.claude/rules`, `.claude/skills`, one `.claude/commands/<workflow>.md` wrapper per workflow, `.claude/CLAUDE.md` with `@AGENTS.md` and `@MEMORY.md` imports, and an ownership-tracked `.claude/settings.json` (`agent: product-owner`, approved `.mcp.json` servers, hooks).
- Claude model profiles: the default `anthropic` profile pins `opus`, `sonnet` or `haiku` per role. Use `--claude-profile none` to inherit the session model. Role agents now declare `tools:`, and both post-task reviewers are read-only.
- JEV native hooks for Claude Code: workflow context, alias-only model routing through the Agent tool, permission decisions, and the reviewer packet. See `docs/jev-integration`.
- Fixed Claude JEV model routing: subagent hand-backs and task notifications no longer replace the original request (before, most spawns after the first fell back to the session model). `AskUserQuestion` and `ExitPlanMode` are no longer sent to JEV as permissions. The session model is now read from the transcript and settings instead of an assumed `sonnet`. Without a confident JEV answer, a Claude subagent now gets its role's model from the Claude profile (for example `developer` → `sonnet`) instead of inheriting the session model, which was often `opus`.
- Telegram notifications for Claude Code and Codex through native hooks (`Stop`, plus waiting-for-input events), using one shared runtime, `.agent/notify/telegram.py`. New flags: `--enable-telegram` and `--disable-telegram`. Credentials stay in `~/.config/agentic/config.json`. See `docs/notifications`.
- OpenCode Telegram plugin rewritten for the OpenCode V2 plugin API (V2 did not load the old plugin). It now also reports waiting for input (`permission.asked`, `question.asked`), skips subagent sessions, and sends through the shared runtime.
- Telegram messages on all hosts render agent Markdown as Telegram HTML (code, bold, links, lists, tables as monospace blocks) and fall back to plain text when Telegram rejects the markup. The header names the project and host; the `📊 +0 -0` line is gone.
- Upgrade removes `telegram-notification` and `agent-model-mapper` from the `opencode.json` `plugin` array: they are local plugins, and OpenCode V2 tried to install them from npm (404).
- SDLC roster on all hosts: product-owner → team-lead → developer → qa → optional devops-engineer → post-task review. `pm` and `analyst` are optional. OpenCode `permission.task` now allows devops-engineer, and allows the reviewers from every coordinator. The reviewers are denied edit and bash.
- **Role renames (migration):** `designer` → `analyst` (system analyst), `instruction_reviewer` → `instruction-reviewer`, `memory_curator` → `memory-curator`. Install and upgrade remove unmodified old role files and old OpenCode role keys. Edited files are kept, with a warning. The JEV runtime accepts both spellings.
- All 98 skills now carry valid `name` and `description` frontmatter, and `lint_prompts.py --strict` enforces it. Added `make blackbox-claude`, which runs a real Claude CLI with JEV, a fake Telegram API, and checks that agents, commands, skills and rules load. Added `make test-notify`.
- Blackbox: one bounded approval follow-up on every host, Telegram check on every host, `BLACKBOX_CODEX_SANDBOX` for hosts that block bubblewrap, OpenCode default model `openai/gpt-6-luna`, and operator-spelling dialects in the calculator probe.
- Operational: Python 3.10+ is required when JEV or Telegram is enabled (the OpenCode plugin now calls Python too). Codex Telegram hooks need a `/hooks` trust review.

## v1.3.0

- Added opt-in JEV native hooks for Codex and OpenCode V2 (2.0.28+), replacing the shared skill and workflow-specific checkpoints. Hooks select an installed workflow and an available subagent model; explicit user selections remain authoritative.
- Preserved TUI activation and masked key entry. The official TypeSafe AI server remains the default, with CLI/environment overrides for the paid test gateway.
- Permission hooks retain sandbox restrictions and native denials. Sensitive or unbounded operations require normal user approval; failures and low-confidence responses fall back to native behavior.
- Local cleansed JEV Q/A and routing evidence are retained for 30 days and included in the existing advisory review pipeline. Unknown prices or application evidence are reported explicitly.
- Added opt-in `make blackbox` checks with real local Codex/OpenCode and the calculator prompt; ordinary tests and CI do not make paid requests. Codex requires native hook trust review.
- Install/upgrade now ignore `.agentic*/` and `.review*/` directories without ignoring `.agentic.json`. Existing local review artifacts are no longer tracked.
- Fixed Windows knowledge-base path normalization for Codex model routing; bundled model defaults remain open when JEV is enabled, while user pins and explicit agent limits are preserved.
- Limited JEV model candidates to project role defaults intersected with the host catalog. Hook sources now live under each environment's `extensions/<host>/hooks/` directory.
- Root guidance requires customer approval for new repository-root files and uses an approximate 80% simplified technical writing target, preserving precision for complex material.

## v1.2.0

- Upgrade now synchronizes using the newly installed executable and supports an explicit project directory.
- Smart project upgrades adopt recognizable legacy artifacts, merge local guidance edits using generated baselines, and back up conflicts before replacing them. Fully user-owned instructions are preserved with a manual-integration report.
- Added `upgrade --force` to rebuild recognized Agentic artifacts without prompts, replaying manifest settings or falling back to `default + software.general` with optional integrations off.
- Project updates are staged, backed up privately under `.agentic-backups/`, and restored on application failures. Shared configurations retain unrelated fields; global settings are preserved.
- Manifest v2 remains compatible with v1. The first upgrade of customized v1 instructions without a baseline replaces them with backup. Exclude backups from source control; they can contain project credentials.
- Fixed Windows release ZIP extraction and added executable validation before binary replacement.

## v1.1.0

- Added automatic, compact instruction and documentation/memory reviews after successful top-level delivery in six core SDLC workflows, across Claude, Codex, OpenCode, and existing Gemini profiles.
- Installed a shared on-demand REVIEW_PIPELINE.md protocol with read-only specialists, advisory recommendations, bounded evidence/searches, and non-blocking failure reporting.
- Preserved user-modified managed guidance on upgrades; review hooks or profiles skipped by managed-file protection must be reconciled manually. No memory migration or automatic recommendation application is performed.

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
