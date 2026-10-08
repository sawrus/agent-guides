# Smart project upgrades

`agentic upgrade [--project-dir <path>] [--force] [--dry-run]` updates the release
binary and then synchronizes instructions with the newly installed executable.
An explicit `AGENTIC_KB_DIR` retains priority. Without that override, upgraded
release instructions come from the new binary.

## Requirements and acceptance

- Replay valid manifest settings without prompts or TUI. If settings are absent
  or invalid, use `default`, `software`, `software.general`, with MCPs/plugins off.
- Adopt recognizable Agentic artifacts omitted from the manifest. Preserve fully
  user-owned files, including AGENTS.md, and report manual integration needs.
- Merge non-overlapping edits using a stored generated baseline. On conflict or
  missing baseline, install the current template and retain the local copy in backup.
- Remove obsolete unchanged instructions. Preserve obsolete customized instructions
  during normal upgrades; force removes all recognized Agentic instructions.
- Preserve unrelated keys in shared configurations and all global configuration.
- Reject escaping paths and symlink targets before any project mutation.
- Prepare the complete update in isolation, back up changes, and restore project
  files if applying them fails. Doctor and MemPalace maintenance run after commit.
- Dry runs perform no release downloads or project writes and show the same file
  actions as real synchronization using the currently available payload.

## Design

Project updates render into a private temporary staging directory. Both generation
and cleanup operate there. A file delta is validated against the target project,
then backed up and applied. Manifest v2 references generated instruction baselines
under `.agentic/baselines/`; configuration contents and secrets are excluded.
The stored baseline is the generated template, never the customized merge result.
Manifest v1 remains readable; its first upgrade falls back to replacement with backup
when a local modification cannot be merged without a baseline.

Force rebuilds recognized project artifacts with the replayed settings. Shared
JSON/TOML files are cleaned by owned sections and regenerated while preserving
unrelated content. Directories are not recursively removed from the actual project.
Backup runs live under `.agentic-backups/<run-id>/`, with private permissions and
`journal.json` describing restoration. Backups can contain credentials; keep them
private and outside source control. Successful binary upgrades are not rolled back.
