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

`agentic install` and `agentic tui` fail fast when required local tools are missing:

- Bash 3.2+.
- Python 3 as `python3`.
- pip as `pip3`, `pip`, or `python3 -m pip`.
- `shasum` or `sha256sum` for managed-file hashes.
- Git when installed mode needs to bootstrap or upgrade `~/.local/share/agentic/repo`.

Optional tools:

- `fzf` for interactive picker UI; index-based menus are used when it is unavailable.
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
- `--install-fzf`: optionally try auto-installing `fzf` during self-install
- `--dry-run`: show actions without writing files

## Core commands

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

After install, `agentic` writes `.agentic.json` in the target project. It records copied/generated files and their hashes. A later install rerun updates only manifest-managed files and skips files changed by the user. Generated guidance is always written to root `AGENTS.md`; when OpenCode is selected, `agentic` also writes `.opencode/AGENTS.md`.

When Codex is selected, `agentic` creates or updates the project-local `.codex/config.toml` with Codex memories enabled:

```toml
[features]
memories = true
```

This config file follows the same manifest-managed safeguards as other generated project files.

After the project files are generated, `agentic` starts timestamped operational logging and mirrors install output to a temporary log file such as:

```text
/tmp/agentic-20260512-114203.ABC123
```

The final install line prints the exact path:

```text
Agentic log file: /tmp/agentic-20260512-114203.ABC123
```

`agentic` also runs a final doctor smoke check for selected real agent targets (`codex`, `opencode`, `claude`, `gemini`). The doctor runs in a temporary copy of the project and prints one status row per selected agent. All supported doctor targets use a lightweight pure smoke prompt, so install-time doctor checks do not start a long SDLC workflow. Each agent has an independent timeout controlled by `AGENTIC_DOCTOR_TIMEOUT_SECONDS` and defaults to `10` seconds. Doctor failures and timeouts are reported but do not roll back or fail the install. Disable doctor for cheap checks with:

```bash
AGENTIC_DOCTOR=0 agentic install ...
# or
agentic install ... --no-doctor
```

List available options:

```bash
agentic list agentos
agentic list areas
agentic list specs --area software
```

Refresh the local knowledge base checkout:

```bash
agentic upgrade
```

In installed mode, `agentic upgrade` also refreshes the installed `agentic` binary from the updated knowledge base checkout. If an older binary cannot self-update, use the `curl ... | bash -s -- --force` bootstrap command above once.

## TUI and `fzf`

TUI uses `fzf` for interactive selection. If `fzf` is missing, `agentic` can:

1. ask permission to auto-install it
2. fall back to index-based menus if install is declined or fails

`--install-fzf` only affects `self-install`. If auto-install fails, self-install still completes.

The CLI supports the system bash 3.2 shipped with macOS and does not require installing a newer bash.

Manual install examples:

Linux:

```bash
sudo apt-get install -y fzf
```

macOS:

```bash
brew install fzf
```

Windows (run from Git Bash):

```bash
winget install --id junegunn.fzf -e
# or
choco install fzf -y
# or
scoop install fzf
```

## OpenCode optional plugins

When `opencode` is selected, interactive installs ask whether to enable `Telegram Notifications` and `Agent Model Mapping`. These are readable menu labels for the stable internal ids `telegram-notification` and `agent-model-mapper`. The answer is stored globally in:

```text
~/.config/agentic/opencode-plugins.json
```

Non-interactive installs create a disabled config when no config exists. Interactive installs ask for Telegram `botToken` and `chatId` when `telegram-notification` is selected. Those credentials are written to the target project `.agentic.json` under `settings.opencode_plugins.telegram`, not to `~/.config/agentic/opencode-plugins.json`. Treat `.agentic.json` as plaintext secret-bearing project config when Telegram is enabled and do not commit it to public repositories. When enabled, `agent-model-mapper` runs during interactive `agentic install`/`agentic tui`, uses `fzf` as a dropdown picker when available, and writes `.opencode/opencode.json` only after a Confirm action. OpenCode startup does not load a mapper runtime plugin or prompt for model mapping.

OpenCode model profiles are stored in `extensions/opencode/profiles` and appear in the same optional OpenCode selection menu as the plugin choices. The built-in choices are `OpenAI Model Profile` and `GitHub Copilot Model Profile`; non-interactive installs can choose them with `AGENTIC_OPENCODE_PROFILE=openai` or `AGENTIC_OPENCODE_PROFILE=githubcopilot`. Users can add local profiles under `$HOME/.config/agentic/opencode/profiles/<profile-id>/opencode.json`; for example, `DT/opencode.json` appears as `DT profile` and `GH/opencode.json` appears as `GH profile`. Profile selection merges agent model mappings into `.opencode/opencode.json`, then MCP configuration is merged afterward.

OpenCode MCP config uses top-level `mcp`, not `mcpServers`. Agentic migrates legacy OpenCode `mcpServers` entries into `mcp` during install. Codex continues to use `.codex/config.toml` with `[mcp_servers.*]` sections.

For selected Kubernetes and Docker MCP integrations, `agentic` performs non-fatal local checks after config generation: `kubectl version` for Kubernetes and `docker mcp --version` for Docker MCP. Failed checks appear as warnings in the final install report with official setup links. Docker MCP server entries are generated under the server name `docker`.

## Context7

For `opencode`, `codex`, `claude`, `cursor`, `gemini`, `kilocode`, and `antigravity`, interactive installs ask whether to add Context7 MCP configuration. If enabled, a follow-up menu chooses either keyless mode or entering `CONTEXT7_API_KEY`. The selected key is written to all selected target configs for the current project. Most targets use project-level files, while `antigravity` is written to the global user path `~/.gemini/antigravity/mcp_config.json`.

Non-interactive installs enable Context7 when either `AGENTIC_ENABLE_CONTEXT7=y` or `CONTEXT7_API_KEY` is set. Agents are instructed to use Context7 for framework, library, SDK, API, and setup documentation when the project config is present.

## MemPalace

For `opencode`, `codex`, `claude`, `cursor`, `gemini`, `kilocode`, and `antigravity`, MemPalace MCP is configured as a local Python module instead of a hosted MCP URL. When MemPalace is enabled, `agentic` attempts to install it automatically with `pip install mempalace`.

Generated configs run `mempalace-mcp` without arguments for all supported agent targets. Runtime startup and MCP tool errors are checked by the post-install doctor stage.

During install, if MemPalace is enabled, `agentic` writes a managed `.mempalaceignore` when the target project does not already have one. It initializes the project with `mempalace init --yes --no-llm`, then mines project knowledge into a wing named from the target project basename. If `docs/` exists, those files are also mined into the shared `shared_docs` wing for cross-project Markdown knowledge. MemPalace commands time out after `60` seconds by default; override with `AGENTIC_MEMPALACE_TIMEOUT_SECONDS`. If auto-install, initialization, mining, timeout, or runtime checks fail, install continues, manual setup instructions are printed, and agents fall back to standard context discovery. If `pip install mempalace` fails, `agentic` prints the pip exit status, a temporary pip output log path, and the first non-empty pip output line as the likely reason; the full pip output is also copied into the main Agentic run log.

For environments that already provide `mempalace-mcp` and need a fast install path, set `AGENTIC_MEMPALACE_SETUP=skip`. This writes the same MCP configuration and `.mempalaceignore` but skips Python package installation and project indexing.

## Real agent blackbox E2E

`make test` runs the fast deterministic e2e suite and is intended to finish in under a minute on a normal local machine. Longer deterministic checks (`test-doctor`, `test-markers`), real-agent blackbox, and coverage checks are explicit targets so the default local loop stays short.

`make test-real-blackbox` validates real Codex/OpenCode install artifacts, generated guidance, MCP config, and manifest evidence without starting live LLM sessions by default. Set `AGENTIC_REAL_BLACKBOX_LIVE=1` to execute live `codex`/`opencode` runs. Live Telegram checks require Telegram credentials to be present in the target project `.agentic.json`; secrets are redacted from test output.

Makefile test targets print timestamped `[make-timing]` start, success/failure, exit status, and elapsed seconds for every top-level test step. `test-real-blackbox` is split into separate Codex, OpenCode, OpenCode mapper, and Telegram timed steps. Blackbox instruction evidence is saved to a `/tmp/agentic-instruction-evidence.*` file and the path is printed. `test-coverage` also prints timing for each traced coverage scenario before the final coverage parser. Use `make test-all` when you want the fast suite, longer deterministic checks, install/evidence blackbox, and coverage in one command.

```bash
make test-real-blackbox
AGENTIC_REAL_BLACKBOX_LIVE=1 make test-real-blackbox
```

## Deprecated wrapper

`agentos-install.sh` remains for backward compatibility and forwards to `agentic`. Prefer `agentic` in new usage and documentation.
