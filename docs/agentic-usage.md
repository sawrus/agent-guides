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
curl -fsSL https://raw.githubusercontent.com/sawrus/agent-guides/main/install | bash
```

The bootstrap script runs `self-install` with `--force` by default, so a plain `curl ... | bash` refreshes the installed binary.

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

In installed mode, `agentic upgrade` also refreshes the installed `agentic` binary from the updated knowledge base checkout. If an older binary cannot self-update, use the `curl ... | bash` bootstrap command above once.

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

When `opencode` is selected, interactive installs ask whether to enable Telegram notifications and the model checker. The answer is stored globally in:

```text
~/.config/agentic/opencode-plugins.json
```

Non-interactive installs create a disabled config when no config exists. Telegram can also read `OPENCODE_TELEGRAM_BOT_TOKEN` and `OPENCODE_TELEGRAM_CHAT_ID`.

## Context7

For `opencode` and `codex`, interactive installs ask whether to add project-level Context7 MCP configuration. If enabled, the Context7 API key prompt is optional; leave it empty to configure Context7 without a key.

Non-interactive installs skip Context7 unless `CONTEXT7_API_KEY` is set in the environment. Agents are instructed to use Context7 for framework, library, SDK, API, and setup documentation when the project config is present.

## Deprecated wrapper

`agentos-install.sh` remains for backward compatibility and forwards to `agentic`. Prefer `agentic` in new usage and documentation.
