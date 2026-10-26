# Release policy

agentic uses versions of the form `MAJOR.MINOR.PATCH`. The version lives in `Cargo.toml` and `package.json`.
Both must match (`make check-version-sync`).

Every change ships as its own version. `CHANGELOG.md` has no `## Unreleased` section.

## Which number to bump

| Bump | When | Examples |
|---|---|---|
| MAJOR | A new feature, or a change that breaks existing installs or habits. | A new command, profile kind, tool, or opt-in hook. A changed default, installed file layout, or `.agentic.json` format. A removed or renamed CLI flag or command. |
| MINOR | A fix. | A broken hook path, a wrong default model id, a failing doctor check. |
| PATCH | A change that does not change what agentic does: documentation, CI, tests, refactoring. | A doc error, a CI job fix. |

If one PR mixes kinds, the largest kind wins: a feature with fixes is MAJOR.

## Rules

- Every PR that changes the repository bumps the version itself and adds its entries under `## vX.Y.Z` at the
  top of `CHANGELOG.md`. Do not write `## Unreleased`.
- The new version is the next one after the version on `main`. If `main` moves before the merge, rebase and take
  the next free version again.
- A breaking change adds a migration section to `UPGRADE.md`, and its CHANGELOG entry starts with `Breaking:`.

## Release steps

1. In the PR: set the version in `Cargo.toml` and `package.json`, refresh `Cargo.lock` (`cargo build`), and add
   the `## vX.Y.Z` section to `CHANGELOG.md`.
2. Run `make test` and `make lint`. All must pass.
3. Open the PR. CI must pass on Linux, macOS, and Windows.
4. After the merge, tag the merge commit `vX.Y.Z` and publish the GitHub release with the CHANGELOG section as
   notes.
