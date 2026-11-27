---
covers:
  - src/kb.rs
  - src/selfinstall.rs
  - src/upgrade.rs
  - src/legacy.rs
  - bin/agentic.js
  - install
---

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

The install-time OpenCode doctor smoke check does not reuse the user's live OpenCode session state. Instead, Agentic creates a temporary XDG home for that doctor run, copies only the OpenCode config directory, `auth.json`, cached `models.json`, and the provider credentials from `opencode.db` (the `credential` and account tables; every other table is emptied), and lets any temporary OpenCode session live only inside the doctor temp root. It passes `--model`: `AGENTIC_DOCTOR_OPENCODE_MODEL` if set, else `model` from the project or global OpenCode config, else the model the user picked last (`recent[0]` in `state/opencode/model.json`), and sets `OPENCODE_DISABLE_MODELS_FETCH=1` when `models.json` is cached. To fit the timeout, it reuses the user's npm cache (`~/.npm`, unless `npm_config_cache` is set) so `npx` MCP servers are not downloaded again, and sets `OPENCODE_DISABLE_FILEWATCHER=1`.

Before each doctor run, Agentic removes leftover `$TMPDIR/agentic-*` directories from earlier runs. It first stops the processes still running in them (Linux), then deletes the agent sessions that ran in them: Codex threads (`codex delete --force`), OpenCode sessions (`opencode session delete`), and Claude Code project transcripts under `~/.claude/projects`. The directory that holds the target project and the run log files are kept. After the smoke checks, the doctor also stops processes left in its own temp root, such as MCP servers that outlived the agent.

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

The session-start hook of the quality gate reminds about new releases once per interval and only offers the
upgrade; see [upgrade reminder](upgrade-reminder.md).

## Managed reruns

When `.agentic.json` exists in the target project, `agentic install` treats the project as already managed:

- only files listed in `.agentic.json` are eligible for update;
- files whose current hash differs from the stored hash are skipped as user-modified;
- new hashes are written for successfully updated managed files;
- skipped paths are recorded in `.agentic.json`.

Every copied or generated file carries an internal marker. Markdown uses YAML front matter, comment-capable formats use comments, and JSON ownership is recorded in the manifest.
