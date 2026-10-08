# Installed CLI lifecycle

This guide describes how an installed `agentic` binary resolves and updates its knowledge base checkout.

## Paths

`agentic` uses XDG-compatible defaults:

- Config home: `${XDG_CONFIG_HOME:-$HOME/.config}`
- Data home: `${XDG_DATA_HOME:-$HOME/.local/share}`
- Config directory: `~/.config/agentic`
- Config file: `~/.config/agentic/config`
- JSON config file: `~/.config/agentic/config.json`
- OpenCode plugin config: `~/.config/agentic/opencode-plugins.json`
- Knowledge base data directory: `~/.local/share/agentic`
- Knowledge base checkout: `~/.local/share/agentic/repo`

The config file currently stores the selected theme:

```ini
theme=auto
```

Supported values are `auto`, `dark`, and `light`.

Target projects receive `.agentic.json`. It stores selected install settings, optional project-level OpenCode plugin enablement, managed file paths, source paths, hashes, generated marker type, and skipped files from the latest rerun. When Telegram notifications are enabled, raw `botToken` and `chatId` values are stored in `$HOME/.config/agentic/config.json`, while `.agentic.json` stores enablement only.

The install-time OpenCode doctor smoke check does not reuse the user's live OpenCode session state. Instead, Agentic creates a temporary XDG home for that doctor run, copies only the OpenCode config directory plus `auth.json` and cached `models.json`, and lets any temporary OpenCode session database live only inside the doctor temp root.

## Instruction sources

The standalone Rust binary embeds the knowledge base. It needs no cloned checkout.
An explicit `AGENTIC_KB_DIR` selects a development payload; otherwise a neighboring
valid checkout takes priority during development. A process launched after binary
replacement uses the newly embedded payload unless `AGENTIC_KB_DIR` is explicit.

## Upgrade flow

```bash
agentic upgrade [--project-dir <path>] [--force] [--dry-run]
```

Upgrade fetches the latest GitHub release, validates its executable, replaces the
installed binary, and launches project synchronization using the new executable.
It synchronizes even when the installed binary is already current. By default the
target is the current directory; `--project-dir` selects an explicit project.

Recognizable legacy artifacts and manifest-owned instructions are updated.
Non-overlapping local edits are merged against stored generated baselines;
conflicts and customized files without a baseline are replaced with backup.
Fully user-owned guidance stays untouched and is reported for manual integration.

`--force` rebuilds recognized Agentic artifacts without questions or TUI, retaining
unrelated project files and global configuration. Valid settings are replayed;
missing or invalid settings default to `default + software.general`, with optional
MCPs and plugins disabled. Without force, a directory with neither a manifest nor
recognized artifacts receives only the binary upgrade.

Project updates are prepared in isolation, backed up privately, and restored if
applying files fails. The successfully updated binary remains installed. Dry runs
show project actions using the available payload without downloading a release or
changing the target project. See [the full upgrade contract](agentic-upgrade/README.md).

## Managed reruns

When `.agentic.json` exists in the target project, `agentic install` treats the project as already managed:

- only files listed in `.agentic.json` are eligible for update;
- files whose current hash differs from the stored hash are skipped as user-modified;
- new hashes are written for successfully updated managed files;
- skipped paths are recorded in `.agentic.json`.

Every copied or generated file carries an internal marker. Markdown uses YAML front matter, comment-capable formats use comments, and JSON ownership is recorded in the manifest.

## MemPalace install and validation logs

When MemPalace MCP is enabled during interactive install, TUI install, or through `AGENTIC_ENABLE_MEMPALACE=y`, `agentic` now reports setup progress in explicit steps so users can see what succeeded or failed:

1. Python availability check
2. pip availability check
3. `pip install mempalace`
4. Project memory initialization with `mempalace init --yes --no-llm`
5. Project mining with `mempalace mine <project> --wing <project-basename>`
6. Optional shared docs mining with `mempalace mine <project>/docs --wing shared_docs`

If auto-install, initialization, mining, or runtime checks fail, `agentic` prints manual setup instructions and continues. When `pip install mempalace` fails, the warning includes the pip exit status, a temporary pip output log path, and the first non-empty pip output line as the likely reason. The full pip output is also copied into the main Agentic run log. After setup, install checks that `mempalace-mcp` is present and leaves runtime startup/tool validation to the post-install doctor smoke check. Generated MCP configs invoke `mempalace-mcp` without arguments for all supported agent targets.

Each MemPalace init/mine command has a timeout controlled by `AGENTIC_MEMPALACE_TIMEOUT_SECONDS` and defaults to `60` seconds. Timeouts are reported as warnings and do not block MCP config generation.
