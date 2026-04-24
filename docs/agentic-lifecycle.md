# Installed CLI lifecycle

This guide describes how an installed `agentic` binary resolves and updates its knowledge base checkout.

## Paths

`agentic` uses XDG-compatible defaults:

- Config home: `${XDG_CONFIG_HOME:-$HOME/.config}`
- Data home: `${XDG_DATA_HOME:-$HOME/.local/share}`
- Config directory: `~/.config/agentic`
- Config file: `~/.config/agentic/config`
- OpenCode plugin config: `~/.config/agentic/opencode-plugins.json`
- Knowledge base data directory: `~/.local/share/agentic`
- Knowledge base checkout: `~/.local/share/agentic/repo`

The config file currently stores the selected theme:

```ini
theme=auto
```

Supported values are `auto`, `dark`, and `light`.

Target projects receive `.agentic.json`. It stores selected install settings, managed file paths, source paths, hashes, generated marker type, and skipped files from the latest rerun.

## Repository modes

`agentic` supports two repository source modes:

1. Dev mode: when `agentic` runs from a real `agent-guides` checkout and can find sibling `areas/`, `extensions/`, and `AGENTS.md`, it uses the local repository directly.
2. Installed mode: when the binary is installed to a standalone path such as `~/.local/bin/agentic`, it uses `~/.local/share/agentic/repo` as knowledge base checkout.

## Bootstrap

In installed mode, commands that need repository data clone the checkout on first use:

```bash
git clone https://github.com/sawrus/agent-guides.git ~/.local/share/agentic/repo
```

After cloning, `agentic` validates that the checkout contains:

- `areas/`
- `extensions/`
- `AGENTS.md`

Commands that auto-bootstrap when needed:

- `agentic list ...`
- `agentic install ...`
- `agentic tui`
- `agentic upgrade`

## Upgrade flow

Refresh the knowledge base checkout with:

```bash
agentic upgrade
```

Behavior:

- If `~/.local/share/agentic/repo` does not exist, `agentic upgrade` performs initial clone.
- If checkout already exists, `agentic` runs:

```bash
git -C ~/.local/share/agentic/repo pull --ff-only
```

In dev mode, `upgrade` targets the active local checkout instead of `~/.local/share/agentic/repo`.

## Managed reruns

When `.agentic.json` exists in the target project, `agentic install` treats the project as already managed:

- only files listed in `.agentic.json` are eligible for update;
- files whose current hash differs from the stored hash are skipped as user-modified;
- new hashes are written for successfully updated managed files;
- skipped paths are recorded in `.agentic.json`.

Every copied or generated file carries an internal marker. Markdown uses YAML front matter, comment-capable formats use comments, and JSON uses an `_agentic` object.
