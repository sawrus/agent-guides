---
covers:
  - src/main.rs
  - src/app.rs
  - src/tui.rs
  - src/ui.rs
  - src/theme.rs
  - src/install.rs
  - src/prompt.rs
  - src/config.rs
---

# agentic CLI usage

This guide covers day-to-day use of the `agentic` CLI.

For lifecycle and repository resolution details, see [Installed CLI lifecycle](agentic-lifecycle.md).

## Run modes

Run from a local checkout:

```bash
./agentic
```

Run directly with NPX (no prior install):

```bash
npx @jetrabbits/agentic@latest
```

Run the installed binary:

```bash
agentic
```

Default behavior:

- In an interactive terminal: starts TUI mode
- In non-interactive mode (CI/pipe): prints usage and exits with code `1`
- For CI one-off execution, prefer `npx @jetrabbits/agentic@latest <command>`

## Requirements

The core installer is a self-contained Rust binary. Unix release upgrades use `tar`.
Selected integrations may require their own runtimes. No Git checkout is required for installed use.

Optional tools:

- Built-in ratatui fullscreen wizard for interactive picker UI; no external `fzf` dependency is required.
- Node.js/npm only for the `npx @jetrabbits/agentic@latest` entrypoint.
- `curl` only for the bootstrap installer.
- Real agent binaries only for selected target recommendations and doctor checks.

Install the standalone binary:

```bash
./agentic self-install
```

For users with an old installed `agentic`, do not run `agentic self-install --force` from `$PATH`: that invokes the old binary and may try to copy itself over itself. From a fresh `agent-guides` checkout, run from the repository root instead:

```bash
./agentic self-install --force
```

Recover or update an already installed binary without relying on the old local copy:

```bash
curl -fsSL https://raw.githubusercontent.com/sawrus/agent-guides/main/install | bash -s -- --force
```

Common options:

- `--bin-dir <dir>`: install into a custom binary directory
- `--force`: overwrite an existing target binary
- `--dry-run`: show actions without writing files

## Core commands

### Optional JEV native hooks

Select `jev` beside Context7 in TUI. The server defaults to the official TypeSafe
AI API without a picker. Use `--jev-api-url` or `JEV_API_URL` for your test server.
For a non-interactive install:

```bash
agentic install --project-dir /path/to/project --agent-os codex,opencode,claude \
  --areas software --specializations software.backend \
  --enable-jev --no-doctor
```

Use `--disable-jev` on a later install to turn it off. The project manifest stores
`settings.jev.enabled/api_url`; keys stay in environment or project `.env`.
Hosted uses `JEV_API_KEY`; official TypeSafe uses `TYPESAFE_API_KEY`.
No MCP server or extra Rust API client is installed. Native hooks (Codex
`.codex/hooks.json`, OpenCode plugin, Claude `.claude/settings.json`) call
`.agent/jev/hook.py`. See [activation and local checks](jev-integration/README.md).

### Telegram notifications and Claude model profiles

```bash
agentic install --project-dir /path/to/project --agent-os claude,codex \
  --areas software --specializations software.backend \
  --enable-telegram --claude-profile anthropic --no-doctor
```

`--enable-telegram` / `--disable-telegram` control notifications on every host
(OpenCode plugin, Claude and Codex hooks); see [notifications](notifications/README.md).
`--claude-profile anthropic|none` (or `AGENTIC_CLAUDE_PROFILE`) pins or clears
per-role model aliases in `.claude/agents`; see [Claude Code](claude-code/README.md).

### Role profiles

A role profile picks the agent files per host. `lean` (default) installs `explorer` and keeps the native
main session. A custom profile can add the `reviewer` helper (`"agents": ["explorer", "reviewer"]`). `team` installs the 9 SDLC roles. Custom profiles live in
`~/.config/agentic/<host>/profiles/<id>/profile.json`:

```json
{"name": "my", "base": "team", "agents": ["developer", "qa"], "models": null}
```

```bash
agentic profile list                      # every host; add --host claude|codex|opencode
agentic profile create my --from team     # copies the team roles; edit the file afterward
agentic profile show my --host claude
agentic profile use team --project /path/to/project
agentic profile use lean --host codex     # one host only, project = current directory
agentic install ... --profile claude=team,codex=lean
```

`agentic profile use` reinstalls the project through the upgrade path. It removes the unmodified role files of
the old profile, keeps the files you edited, and saves the choice in `.agentic.json`. Restart the agent session
afterward; hosts load agents only at session start. Inside a session use `/profile team` (Claude Code,
OpenCode) or ask Codex to switch the profile (skill `agentic-profile`), or run `! agentic profile use team` in
the Codex prompt. See [reference](agentic-reference.md#role-profiles-all-hosts) for the file format.

### Company rules

Company rules come from a directory or a git repository and override pack rules on the same topic:

```bash
agentic install --project-dir /path/to/project --agent-os claude,codex \
  --areas software --specializations software.backend \
  --company-rules-git 'git@gitlab.example.com:group/standards.git#main:rules' \
  --company-rules-exclude software/backend/testing
```

`--company-rules-path <dir>` adds a local directory. Install copies the rules into `.agent/company/` (Claude Code
also gets `.claude/rules/company-*.md`), skips the excluded pack rules and the ones named in `replaces:`, and
prints the pack rules that company rules duplicate. `agentic upgrade` fetches the git source again. See
[company rules](company-rules.md).

### Skill packs

Skill packs are ready-made skills from a git repository or a directory. agentic installs them unchanged on every
selected host:

```bash
agentic install --project-dir . --agent-os claude,codex,opencode --areas software \
  --specializations software.backend --skill-pack 'https://github.com/mattpocock/skills#main'
agentic skills add https://github.com/mattpocock/skills --id pocock --select tdd,grill-me
agentic skills list
agentic skills update pocock
agentic skills remove pocock
```

A skill is any directory with `SKILL.md` below `skills_root` (default `skills`); nested categories are
flattened. The manifest locks the commit of a git pack; `agentic skills update` moves the lock. A skill name that
clashes with another skill is an error. See [skill packs](skill-packs.md).

The built-in preset `pocock` installs 21 skills of mattpocock/skills (MIT, Matt Pocock) at a pinned commit and
sets up the project for them. `--issue-tracker local|github|gitlab` (default `local`) writes
`docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md`, `docs/agents/domain.md`, and an
`## Agent skills` section in the generated AGENTS.md:

```bash
agentic install --project-dir . --skill-pack pocock --issue-tracker gitlab
agentic skills add pocock --issue-tracker github
```

Two more presets need no setup: `superpowers` installs 13 skills of obra/superpowers (MIT, Jesse Vincent), and
`anthropic` installs 9 developer skills of anthropics/skills (Apache-2.0 per skill, Anthropic):

```bash
agentic skills add superpowers
agentic install --project-dir . --skill-pack anthropic
```

Start TUI:

```bash
agentic tui
```

Install guidance into a project:

```bash
agentic install \
  --project-dir /path/to/your-project \
  --agent-os opencode,codex \
  --areas software \
  --specializations software.general,software.backend
```

After install, `agentic` writes `.agentic.json` in the target project. It records copied/generated files and their hashes. A later install rerun updates only manifest-managed files and skips files changed by the user. By default generated guidance is written to root `AGENTS.md`; when OpenCode is selected, `agentic` also writes `.opencode/AGENTS.md`. With `--agents-md keep` root `AGENTS.md` belongs to the project, and the generated guidance goes to `.agent/AGENTS.md`, `AGENTS.override.md` (Codex), and the OpenCode plugin `.opencode/plugins/agentic-agents-md.ts`, which adds `.agent/AGENTS.md` to every request ([details](agentic-reference.md#root-agentsmd-generate-or-keep)).

When Codex is selected with the `team` profile, `agentic` creates or updates the project-local `.codex/config.toml` with Codex memories enabled. The `lean` profile leaves memories off, because Codex then adds the user's cross-project memory to every request; on upgrade from `team` it removes the line that `agentic` wrote and keeps a value the user set:

```toml
[features]
memories = true
```

When selected MCP servers need outbound network access, generated Codex config also enables project-scoped workspace network access:

```toml
[sandbox_workspace_write]
network_access = true
```

Generated Codex MCP entries include non-interactive `npx -y` arguments where needed and startup/tool timeouts so first-run package startup does not fail before the MCP server initializes.

This config file follows the same manifest-managed safeguards as other generated project files.

After the project files are generated, `agentic` starts timestamped operational logging and mirrors install output to a temporary log file such as:

```text
/tmp/agentic-20260512-114203.ABC123
```

The final install line prints the exact path:

```text
Agentic log file: /tmp/agentic-20260512-114203.ABC123
```

`agentic` also runs a final doctor smoke check for selected real agent targets (`codex`, `opencode`, `claude`, `gemini`). The doctor runs in a temporary copy of the project and prints one status row per selected agent. All supported doctor targets use a lightweight pure smoke prompt, so install-time doctor checks do not start a long SDLC workflow. OpenCode doctor also runs inside an isolated temporary XDG home: Agentic copies only OpenCode config, `auth.json`, cached `models.json`, and the provider credentials from `opencode.db` into that temp state; it does not copy the user's OpenCode sessions. The smoke check uses `AGENTIC_DOCTOR_OPENCODE_MODEL` if set, else `model` from your OpenCode config, else the model you picked last in OpenCode. Before each run, the doctor deletes leftover `$TMPDIR/agentic-*` directories, the processes still running there, and the Codex, OpenCode, and Claude Code sessions that ran in them. Each agent has an independent timeout controlled by `AGENTIC_DOCTOR_TIMEOUT_SECONDS` and defaults to `10` seconds. Doctor failures and timeouts are reported but do not roll back or fail the install. Disable doctor for cheap checks with:

```bash
AGENTIC_DOCTOR=0 agentic install ...
# or
agentic install ... --no-doctor
```

### Stale-checkout warning

`agentic install` and `agentic upgrade` check the project checkout before the report and the doctor run. The
check reads local git refs only. It does not fetch and never blocks. The origin default branch comes from
`refs/remotes/origin/HEAD`; `ahead` and `behind` come from `git rev-list --left-right --count HEAD...origin/<default>`.

- HEAD is on another branch or detached: warn when HEAD has no own commits (`ahead == 0`) and is behind
  `origin/<default>` (`behind >= 1`). HEAD is then an older copy of the default branch, for example a local `main`
  left behind while origin moved to `master`. A feature branch with its own commits never warns.
- HEAD is on the default branch: warn when it is 20 or more commits behind `origin/<default>`. Local refs can be
  older than the remote, so the real lag can be larger.
- A directory outside git, a repository without `origin/HEAD`, or a git error: no warning.

The warning is one line in the output and in the report `Warnings` list:

```text
[agentic][warn] Stale checkout: HEAD is on branch main, not on the origin default branch master; it has no own commits and is 281 commits behind origin/master, so the code here may be outdated. Run: git switch master && git pull
```

The doctor has no separate command; it runs inside install and upgrade, after this check, so the warning shows
once per run. Agent sessions get the same line once at session start through the quality gate
(`gate.py --event start`): a `SessionStart` hook in Claude Code and Codex, and the `context` hook of the OpenCode
gate plugin. See [quality gate](agentic-v2-lean/README.md#quality-gate).

List available options:

```bash
agentic list agentos
agentic list areas
agentic list specs --area software
```

Update the release binary and project instructions:

```bash
agentic upgrade --project-dir /path/to/project
agentic upgrade --force --dry-run
```

Project synchronization runs with the new executable. Ordinary upgrades merge local
instruction edits where possible and back up replacements. `--force` rebuilds only
recognized Agentic artifacts without prompts. See [upgrade behavior](agentic-upgrade/README.md).

`upgrade` needs `.agentic.json`. In a project with Agentic files but without that file, it stops and asks you
to run `agentic install` (or `agentic tui`) with the intended settings; `agentic upgrade --force` rebuilds with
`default + software.general` instead.

Removed specializations still install: `software.full-stack` becomes `software.backend,software.frontend,software.general`,
and `software.platform` becomes `devops.kubernetes,devops.infrastructure,devops.ci-cd`. `install` and `upgrade`
print a warning and save the new list in `.agentic.json`. An unknown specialization stops the command and lists
the available ones (`agentic list specs --area <name>`).

`agentic` no longer installs `prompts/` files. Each workflow has an `Example request:` line instead; the docs
site shows these lines.

## TUI

The interactive wizard is implemented with ratatui and does not require an external `fzf` binary.
After the Agent OS step it asks for a role profile once per selected host (Claude Code, Codex, OpenCode).
The labels show the roles and the kind, for example `lean · explorer · native main session`,
`team · 9 roles: product-owner, pm, team-lead, …`, or `my · developer, qa · base team · models: anthropic`.
The choice is saved in `.agentic.json` (`settings.profile_ids`).
Right after the integrations step (where you choose JEV), the "Skills" step offers one skill pack: `None`,
the presets mattpocock/skills, obra/superpowers, and anthropics/skills (each row with a short description, the
skill count, the license, and the GitHub stars), or `Custom source…` for a git spec or a directory. The cursor
starts on the saved pack, so Enter keeps it; another choice replaces it. The issue tracker step follows only
for `pocock`. See [skill packs](skill-packs.md#tui).
The last, optional step "Company rules" asks for a directory and a git repository with company rules
([company rules](company-rules.md)); empty answers keep the feature off.

## OpenCode optional plugins

When `opencode` is selected, interactive installs ask whether to enable `Telegram Notifications` and `Agent Model Mapping`. These are readable menu labels for the stable internal ids `telegram-notification` and `agent-model-mapper`. The answer is stored globally in:

```text
~/.config/agentic/opencode-plugins.json
```

Non-interactive installs create a disabled config when no config exists. Interactive installs ask for Telegram `botToken` and `chatId` when `telegram-notification` is selected for the first time, then save those credentials in `$HOME/.config/agentic/config.json` under `opencode.plugins.telegram`. Later interactive `agentic install` and `agentic tui` runs offer to reuse the saved Telegram credentials instead of immediately asking for raw input. The target project `.agentic.json` records Telegram enablement only and does not store raw Telegram secrets. When enabled, `agent-model-mapper` runs during interactive `agentic install`/`agentic tui`, uses `fzf` as a dropdown picker when available, and writes `.opencode/opencode.json` only after a Confirm action. OpenCode startup does not load a mapper runtime plugin or prompt for model mapping. The Telegram plugin targets the OpenCode V2 plugin API and forwards events to the shared `.agent/notify/telegram.py` (installed with it), so OpenCode, Claude Code and Codex send identical messages; see [Telegram notifications](notifications/README.md).

OpenCode model profiles are stored in `extensions/opencode/profiles` and appear in the same optional OpenCode selection menu as the plugin choices. The built-in choices read `models: OpenAI (openai) · role→model` and `models: GitHub Copilot (githubcopilot) · role→model`; non-interactive installs can choose them with `AGENTIC_OPENCODE_PROFILE=openai` or `AGENTIC_OPENCODE_PROFILE=githubcopilot`. Users can add local profiles under `$HOME/.config/agentic/opencode/profiles/<profile-id>/opencode.json`; for example, `DT/opencode.json` appears as `models: DT · role→model`. Profile selection merges agent model mappings into `.opencode/opencode.json`, then MCP configuration is merged afterward.

OpenCode MCP config uses top-level `mcp`, not `mcpServers`. Agentic migrates legacy OpenCode `mcpServers` entries into `mcp` during install. Codex continues to use `.codex/config.toml` with `[mcp_servers.*]` sections. For selected network-backed Codex MCP servers, agentic writes `[sandbox_workspace_write] network_access = true` in the project config so the generated MCPs can start and reach their upstream services in workspace-write mode.

For selected Kubernetes and Docker MCP integrations, `agentic` performs non-fatal local checks after config generation: `kubectl version` for Kubernetes and `docker mcp --version` for Docker MCP. Failed checks appear as warnings in the final install report with official setup links. Docker MCP server entries are generated under the server name `docker`.

## Context7

For `opencode`, `codex`, `claude`, `cursor`, `gemini`, `kilocode`, and `antigravity`, interactive installs ask whether to add Context7 MCP configuration. If enabled, a follow-up menu chooses either keyless mode or entering `CONTEXT7_API_KEY`. The selected key is written to all selected target configs for the current project. Most targets use project-level files, while `antigravity` is written to the global user path `~/.gemini/antigravity/mcp_config.json`.

Non-interactive installs enable Context7 when either `AGENTIC_ENABLE_CONTEXT7=y` or `CONTEXT7_API_KEY` is set. Agents are instructed to use Context7 for framework, library, SDK, API, and setup documentation when the project config is present.

## Real agent blackbox E2E

`make test` runs the fast deterministic e2e suite and is intended to finish in under a minute on a normal local machine. Longer deterministic checks (`test-doctor`, `test-markers`), real-agent blackbox, and coverage checks are explicit targets so the default local loop stays short.

`make test-real-blackbox` validates real Codex/OpenCode install artifacts, generated guidance, MCP config, and manifest evidence without starting live LLM sessions by default. Set `AGENTIC_REAL_BLACKBOX_LIVE=1` to execute live `codex`/`opencode` runs. Live Telegram checks require Telegram credentials to be present in `$HOME/.config/agentic/config.json`; secrets are redacted from test output.

Makefile test targets print timestamped `[make-timing]` start, success/failure, exit status, and elapsed seconds for every top-level test step. `test-real-blackbox` is split into separate Codex, OpenCode, OpenCode mapper, and Telegram timed steps. Blackbox instruction evidence is saved to a `/tmp/agentic-instruction-evidence.*` file and the path is printed. `test-coverage` also prints timing for each traced coverage scenario before the final coverage parser. Use `make test-all` when you want the fast suite, longer deterministic checks, install/evidence blackbox, and coverage in one command.

```bash
make test-real-blackbox
AGENTIC_REAL_BLACKBOX_LIVE=1 make test-real-blackbox
```

## Deprecated wrapper

`agentos-install.sh` remains for backward compatibility and forwards to `agentic`. Prefer `agentic` in new usage and documentation.
