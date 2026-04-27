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

After install, `agentic` writes `.agentic.json` in the target project. It records copied/generated files and their hashes. A later install rerun updates only manifest-managed files and skips files changed by the user.

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

When `agentic upgrade` runs from a project containing `.agentic.json`, it also syncs that project from the upgraded knowledge base using the recorded install settings. Files changed by the user are skipped and recorded in `.agentic.json`; new generated files from the upgraded knowledge base are added when they do not collide with unmanaged project files.

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

For `opencode`, `codex`, `claude`, `cursor`, and `gemini`, `agentic` adds project-level Context7 MCP configuration when possible. The Context7 API key is optional. Agents are instructed to use Context7 for framework, library, SDK, API, and setup documentation.

Generated Context7 config files:

- OpenCode: `opencode.json` (plus `.opencode/opencode.json` for backward compatibility with existing generated extension config)
- Codex: `.codex/config.toml`
- Claude Code: `.mcp.json`
- Cursor: `.cursor/mcp.json`
- Gemini CLI: `.gemini/settings.json`

## Deprecated wrapper

`agentos-install.sh` remains for backward compatibility and forwards to `agentic`. Prefer `agentic` in new usage and documentation.
