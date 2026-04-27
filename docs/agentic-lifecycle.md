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

In installed mode, after the checkout is updated, `agentic upgrade` copies `~/.local/share/agentic/repo/agentic` over the running installed binary when the contents differ. This keeps future `agentic upgrade` runs able to update both the knowledge base and the local executable.

If a user already has an older installed binary that cannot self-update, do not ask them to run `agentic self-install --force` from `$PATH`: that invokes the old binary. Use one of these recovery paths:

From a fresh `agent-guides` checkout, run from the repository root:

```bash
./agentic self-install --force
```

Or refresh through the bootstrap installer, which downloads a fresh script before installing:

```bash
curl -fsSL https://raw.githubusercontent.com/sawrus/agent-guides/main/install | bash -s -- --force
```

After the knowledge base is updated, `agentic upgrade` checks the current working directory for `.agentic.json`. If present, it treats the directory as an already managed project, reloads the recorded `agent_os`, `areas`, and `specializations`, and reruns the install sync against the upgraded knowledge base.

The project sync follows the same manifest protection as `agentic install`: user-modified managed files are skipped, existing unmanaged files are not overwritten, and new generated files from the upgraded knowledge base are added when their target path does not already exist.

## Managed reruns

When `.agentic.json` exists in the target project, `agentic install` treats the project as already managed:

- only files listed in `.agentic.json` are eligible for update;
- files whose current hash differs from the stored hash are skipped as user-modified;
- new hashes are written for successfully updated managed files;
- skipped paths are recorded in `.agentic.json`.

Every copied or generated file carries an internal marker. Markdown uses YAML front matter, comment-capable formats use comments, and JSON uses an `_agentic` object.
