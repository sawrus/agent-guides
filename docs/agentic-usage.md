# agentic CLI usage

`Agentic` means **Agent Intelligence Configuration**.

This guide covers day-to-day usage of the `agentic` utility.

For lifecycle and repository resolution details, see [Installed CLI lifecycle](agentic-lifecycle.md).

## Run modes

Run from a local checkout:

```bash
./agentic
```

Default behavior:

- In an interactive terminal: starts TUI mode
- In non-interactive mode (CI/pipe): prints usage and exits with code `1`

Self-install the standalone binary:

```bash
./agentic self-install
```

Common self-install options:

- `--bin-dir <dir>`: install into a custom binary directory
- `--force`: overwrite an existing target binary
- `--install-fzf`: optionally try auto-installing `fzf` during self-install
- `--dry-run`: show actions without writing files

`--install-fzf` is optional. If auto-install fails, self-install still completes, and TUI falls back to index-based menus.

## Core commands

TUI mode:

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

Upgrade local knowledge base checkout:

```bash
agentic upgrade
```

## TUI and `fzf`

TUI uses `fzf` for hotkeys (Up/Down + Space + Enter). If `fzf` is missing, `agentic` can:

1. ask permission to auto-install it (Linux: `apt/dnf/yum/pacman/zypper/apk`; macOS: `brew`; Windows Git Bash: `winget/choco/scoop`)
2. fall back to index-based menus if install is declined or fails

Manual install examples:

Linux:

```bash
# Ubuntu / Debian
sudo apt-get update && sudo apt-get install -y fzf

# Fedora / RHEL
sudo dnf install -y fzf
# or
sudo yum install -y fzf

# Arch
sudo pacman -Sy --noconfirm fzf

# openSUSE
sudo zypper --non-interactive install fzf

# Alpine
sudo apk add --no-cache fzf
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

`agentos-install.sh` remains for backward compatibility and forwards to `agentic`.
Prefer `agentic` in all new usage and docs.
