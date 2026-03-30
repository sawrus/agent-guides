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
npx agentic@latest
```

Run the installed binary:

```bash
agentic
```

Default behavior:

- In an interactive terminal: starts TUI mode
- In non-interactive mode (CI/pipe): prints usage and exits with code `1`
- For CI one-off execution, prefer `npx agentic@latest <command>`

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

## Deprecated wrapper

`agentos-install.sh` remains for backward compatibility and forwards to `agentic`. Prefer `agentic` in new usage and documentation.
