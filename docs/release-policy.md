# Release policy

agentic uses semantic versions: `MAJOR.MINOR.PATCH`. The version lives in `Cargo.toml` and `package.json`.
Both must match (`make check-version-sync`).

## Which number to bump

| Bump | When | Examples |
|---|---|---|
| MAJOR | A change breaks existing installs or habits. The default behavior changes, the installed file layout changes, the `.agentic.json` manifest format becomes incompatible, or a CLI flag or command is removed or renamed. | v2.0.0: `lean` became the default profile. |
| MINOR | A new feature that keeps existing installs working. | A new command, a new profile kind, a new tool, a new opt-in hook or gate setting. v2.1.0: role profiles and `tools/repo-scan`. |
| PATCH | Only fixes. No new features, no behavior change beyond the fix. | A broken hook path, a wrong default model id, a doc error. |

If one release mixes kinds, the largest kind wins.

## Rules

- A MAJOR release adds a migration section to `UPGRADE.md`, and the CHANGELOG entry starts with `Breaking:`.
- A feature PR adds its entry to `CHANGELOG.md` under `## Unreleased`. It does not bump the version.
- A bugfix PR adds a CHANGELOG entry only. It does not bump the version.
- Only a release PR bumps the version. It collects the Unreleased entries.

## Release steps

1. Create the branch `chore/<task-id>-release-X.Y.Z` from `main`.
2. Rename `## Unreleased` to `## vX.Y.Z` and add an empty `## Unreleased` above it.
3. Set the version in `Cargo.toml` and `package.json`, then refresh `Cargo.lock` (`cargo build`).
4. Run `make test` and `make lint`. All must pass.
5. Open a PR. CI must pass on Linux, macOS, and Windows.
6. After the merge, tag the merge commit `vX.Y.Z` and publish the GitHub release with the CHANGELOG section as notes.
