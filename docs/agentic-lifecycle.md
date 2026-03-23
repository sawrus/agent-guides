# Installed CLI lifecycle

This document describes how installed `agentic` binaries resolve and maintain their knowledge base checkout.

## XDG directories

`agentic` uses XDG-compatible defaults:

- Config home: `${XDG_CONFIG_HOME:-$HOME/.config}`
- Data home: `${XDG_DATA_HOME:-$HOME/.local/share}`
- Config directory: `~/.config/agentic`
- Config file: `~/.config/agentic/config`
- Knowledge base data directory: `~/.local/share/agentic`
- Knowledge base checkout: `~/.local/share/agentic/repo`

The config file currently stores the selected theme:

```ini
theme=auto
```

Supported values are `auto`, `dark`, and `light`.

## Repository resolution modes

`agentic` supports two repository source modes:

1. Dev mode: when `agentic` runs from a real `agent-guides` checkout and can find sibling `areas/`, `extensions/`, and `AGENTS.md`, it uses the local repository directly.
2. Installed mode: when the binary is installed to a standalone path such as `~/.local/bin/agentic`, it uses `~/.local/share/agentic/repo` as knowledge base checkout.

## First-run bootstrap clone

In installed mode, commands that need repository data auto-bootstrap checkout with:

```bash
git clone https://github.com/sawrus/agent-guides.git ~/.local/share/agentic/repo
```

After cloning, `agentic` validates that checkout contains:

- `areas/`
- `extensions/`
- `AGENTS.md`

Commands that auto-bootstrap when needed:

- `agentic list ...`
- `agentic install ...`
- `agentic tui`
- `agentic upgrade`

## Upgrade flow

To refresh the installed knowledge base checkout:

```bash
agentic upgrade
```

Behavior:

- If `~/.local/share/agentic/repo` does not exist, `agentic upgrade` performs initial clone.
- If checkout already exists, `agentic` runs:

```bash
git -C ~/.local/share/agentic/repo pull --ff-only
```

In dev mode, `upgrade` targets the active local checkout resolved next to the script.
