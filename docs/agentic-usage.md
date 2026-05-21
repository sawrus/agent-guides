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

After install, `agentic` writes `.agentic.json` in the target project. It records copied/generated files and their hashes. A later install rerun updates only manifest-managed files and skips files changed by the user. Generated guidance is written to root `AGENTS.md` for most agents and to `.opencode/AGENTS.md` when OpenCode is selected; multi-target installs that include OpenCode and another agent write both files.

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

When `opencode` is selected, interactive installs ask whether to enable Telegram notifications and `agent-model-mapper`. The answer is stored globally in:

```text
~/.config/agentic/opencode-plugins.json
```

Non-interactive installs create a disabled config when no config exists. Telegram reads `OPENCODE_TELEGRAM_BOT_TOKEN` and `OPENCODE_TELEGRAM_CHAT_ID` from the environment only; tokens are not written to `~/.config/agentic/opencode-plugins.json`. When enabled, `agent-model-mapper` runs during interactive `agentic install`/`agentic tui`, uses `fzf` as a dropdown picker when available, and writes `.opencode/opencode.json` only after confirmation. OpenCode startup never prompts for model mapping; the runtime plugin only reports whether install-time mapping is already complete.

## Context7

For `opencode`, `codex`, `claude`, `cursor`, `gemini`, `kilocode`, and `antigravity`, interactive installs ask whether to add Context7 MCP configuration. If enabled, Context7 is configured without a key unless `CONTEXT7_API_KEY` is already set in the environment. The install output prints the generated config path(s) and an example showing where to add the key later. Most targets use project-level files, while `antigravity` is written to the global user path `~/.gemini/antigravity/mcp_config.json`.

Non-interactive installs enable Context7 when either `AGENTIC_ENABLE_CONTEXT7=y` or `CONTEXT7_API_KEY` is set. Agents are instructed to use Context7 for framework, library, SDK, API, and setup documentation when the project config is present.

## MemPalace

For `opencode`, `codex`, `claude`, `cursor`, `gemini`, `kilocode`, and `antigravity`, MemPalace MCP is configured as a local Python module instead of a hosted MCP URL. When MemPalace is enabled, `agentic` attempts to install it automatically with `pip install mempalace`.

Generated configs run `mempalace-mcp` without arguments for all supported agent targets. Runtime startup and MCP tool errors are checked by the post-install doctor stage.

During install, if MemPalace is enabled, `agentic` writes a managed `.mempalaceignore` when the target project does not already have one. OpenCode installs do not run `mempalace init` automatically; project indexing is optional and printed as a manual follow-up. If auto-install or runtime checks fail, install continues, manual setup instructions are printed, and agents fall back to standard context discovery.

## Real agent blackbox E2E

`make test` includes real Codex, OpenCode, and Telegram blackbox scenarios. The local environment must provide working `codex`, `opencode`, Context7/MemPalace access, network access, valid auth, and Telegram credentials in `OPENCODE_TELEGRAM_BOT_TOKEN` and `OPENCODE_TELEGRAM_CHAT_ID`. Secrets are redacted from test output.

```bash
make test-real-blackbox
```

## Deprecated wrapper

`agentos-install.sh` remains for backward compatibility and forwards to `agentic`. Prefer `agentic` in new usage and documentation.
