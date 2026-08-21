# Agentic Rust Rewrite — Work Plan

Status tracking for the full rewrite of `agentic` from Bash (5598 lines) to a
self-contained cross-platform Rust binary.

## Goals

- Single self-contained binary: no runtime dependency on `git`, `curl`, `jq`,
  `python3` (for core flows), `fzf`, `sed`/`awk`, `shasum`.
- Knowledge base (`areas/`, `extensions/`, `AGENTS.md`, `MEMORY.md`,
  `CHANGELOG.md`) embedded into the binary at build time (`include_dir`).
- 100% functional parity with the Bash version: CLI commands/flags/env vars,
  install pipeline, manifest idempotency, MCP writers, TUI wizard mechanics.
- Fullscreen ratatui TUI preserving the linear wizard flow.
- Unit + integration test coverage ≥ 80% enforced via `make test-coverage`.
- Targets: linux x86_64/aarch64 (musl, static), macOS x86_64/arm64,
  windows x86_64.
- `areas/` payload content is not modified — embed only.

## Architecture decisions

| Concern | Bash version | Rust version |
|---|---|---|
| Knowledge base | `git clone` to `~/.local/share/agentic/repo` | embedded via `rust-embed`/`include_dir`; dev checkout next to exe or `AGENTIC_KB_DIR` takes priority |
| Upgrade | `git pull` + copy script | GitHub Releases API via `reqwest`+`rustls`, atomic `self_replace` |
| JSON/TOML editing | python3 heredocs | `serde_json` (preserve_order) + textual TOML editor byte-compatible with the Python regex logic |
| Hashing | `shasum`/`sha256sum` | `sha2` crate |
| TUI | `fzf` menus with numbered fallback | fullscreen `ratatui` + `crossterm`, same wizard steps |
| Doctor timeouts | hand-rolled `kill` loops | native `try_wait` polling with kill |
| MemPalace | pip install + venv fallback | same, optional feature: python3/pip checked only when enabled |
| Version | package.json via `sed` | `CARGO_PKG_VERSION` (kept in sync with package.json) |

## Module map (`src/`)

- `main.rs` — dispatch, byte-compatible usage text, exit codes 0/1 only.
- `app.rs` — application state (mirror of the bash globals), platform detect,
  WSL label.
- `kb.rs` — knowledge base abstraction (Embedded / Checkout).
- `theme.rs` — dark/light/auto (`COLORFGBG`), `NO_COLOR`, ANSI palettes.
- `ui.rs` — `log/warn/error/out`, run log file, changed-paths report.
- `util.rs` — csv split, sha256, path normalization, wing sanitizer.
- `config.rs` — `~/.config/agentic/{config,config.json,opencode-plugins.json}`.
- `markers.rs` — marker injection (md frontmatter with `created_by`
  preservation, JSON reserialize, `//`/`#` comments, shebang handling).
- `manifest.rs` — `.agentic.json` read/write, idempotency (compare ignoring
  `updated_at`/`updated_by`), managed-file protection, replay loading.
- `copydir.rs` — `copy_dir_contents` port (opencode profiles/base-config skip
  rules, skip user-modified/unmanaged/config-marked files).
- `tomledit.rs` — `set_table_key`, `remove_server_block`,
  `enable_codex_memories` (byte-compatible with Python output).
- `mcp.rs` — 8-entry registry, detection of configured MCPs, per-agent JSON and
  codex TOML writers, context7 writers, legacy `mcpServers`→`mcp` migration,
  env sync (`AGENTIC_ENABLE_MCPS`/`_CONTEXT7`/`_MEMPALACE`).
- `agentsmd.rs` — dest-dir mapping per agent OS, AGENTS.md/MEMORY.md generation.
- `install.rs` — 12-step `run_install` pipeline, validation, opencode
  plugins/profile config, report, missing-binary guides, changelog section.
- `mempalace.rs` — optional integration: pip install, PEP 668 venv fallback,
  init/mine with timeout, config writers, `.mempalaceignore`.
- `mapper.rs` — agent-model-mapper: frontmatter roles, model discovery from
  opencode config/auth/models-cache, mapping writer + state file.
- `doctor.rs` — smoke checks for codex/opencode/claude/gemini, isolated
  opencode HOME, fatal-pattern regex, timeout/keep-tmp handling.
- `prompt.rs` — line-based interactive prompts for CLI installs (numbered
  menus, y/N confirms) — parity with the bash no-fzf fallback.
- `tui.rs` — ratatui wizard: theme → banner → project dir → agent OS → MCPs
  (with `[x]` detection) → areas → per-area specs → install. Esc on project
  dir = exit 1; empty spec selection = exit 1 (parity).
- `selfinstall.rs` — copy binary to `~/.local/bin`, PATH export in shell rc,
  `--install-fzf` kept as a deprecated no-op.
- `upgrade.rs` — GitHub Releases latest → version compare → download asset
  `agentic-<arch>-<os>.{tar.gz,zip}` → sha-checked replace → project re-sync
  (replay install + mempalace graph refresh).

## Behavior parity contracts

1. CLI surface: `list [agentos|areas|specs --area <name>]`, `install`, `tui`,
   `upgrade`, `self-install`, `-h/--help`, `-V/--version/version`; unknown
   command/option → usage + exit 1; `--theme v` and `--theme=v` forms.
2. No args: interactive TTY (or `AGENTIC_FORCE_INTERACTIVE=1`) → TUI; else
   usage + exit 1.
3. Env vars honored: `CONTEXT7_API_KEY`, `AGENTIC_ENABLE_MCPS`,
   `AGENTIC_ENABLE_CONTEXT7`, `AGENTIC_ENABLE_MEMPALACE`, `AGENTIC_DOCTOR`,
   `AGENTIC_DOCTOR_KEEP_TMP`, `AGENTIC_DOCTOR_TIMEOUT_SECONDS`,
   `AGENTIC_MEMPALACE_*`, `AGENTIC_OPENCODE_PROFILE`,
   `AGENTIC_PLATFORM_OVERRIDE`, `NO_COLOR`, `COLORFGBG`, `XDG_*`.
4. Install pipeline order identical to bash `run_install`.
5. Manifest: same JSON shape, sorted `managed_files`, `created_at`/`created_by`
   preservation, unchanged-content keeps `updated_at`, rewrite skipped when
   only `updated_at`/`updated_by` differ.
6. Managed-file rules on rerun: skip unmanaged existing targets, skip
   user-modified (hash mismatch), never overwrite `config`-marked files during
   dir copy.
7. Dest mapping: opencode → `.opencode/{rules,skills,commands}` (prompts
   skipped); cursor → `.cursor/{rules,skills}`; kilocode/antigravity →
   `.kilocode/{rules,skills,workflows}`; others → `.agent/<bucket>`; plus the
   implicit `agents` target → `.agent/<bucket>`.
8. Replay mode: `.agentic.json` in cwd or `--project-dir` restores agent_os,
   areas, specs, MCPs, opencode plugins/profile, telegram credentials.
9. Doctor: same agent commands and classification (timeout/exit/fatal regex),
   ✅/❌ output, temp kept on failure or `AGENTIC_DOCTOR_KEEP_TMP=1`.
10. Intentional deviations:
    - `default` agent OS accepted by validation (documented behavior; the bash
      validator rejected it — upstream bug).
    - `upgrade` updates the binary from GitHub Releases instead of git pull
      (knowledge base is embedded).
    - `--install-fzf` is a no-op with a deprecation warning.

## Testing

- Unit tests in every module (theme, markers, manifest, tomledit, mcp, mapper,
  doctor patterns, config, util, kb, tui states + `TestBackend` rendering).
- Integration tests `tests/cli.rs` via `assert_cmd`: real binary runs porting
  the bash e2e scenarios (list/install/idempotency/replay/dry-run/mcp env/
  context7/self-install/tui non-interactive/validation errors).
- Coverage gate: `cargo llvm-cov --fail-under-lines 80` via
  `make test-coverage`.

## Tooling updates

- `Makefile`: `build`, `test` (cargo test), `test-coverage`, `lint`
  (fmt --check + clippy -D warnings), `fmt`, `clean`, `release-build`;
  content-tooling targets (lint-prompts, sync-diagrams, assess-areas,
  build-docs-catalog) preserved.
- `install` script: downloads the platform binary from GitHub Releases
  (only the bootstrap script itself needs curl/wget).
- `README.md`, `CHANGELOG.md` (v0.7.0), `UPGRADE.md` migration notes.
- Removed: bash `agentic`, `bin/agentic.js` npm wrapper, `tests/e2e/*.sh`,
  coverage shims.

## CI/CD (`.github/workflows/`)

- `ci.yml`: fmt + clippy + tests on ubuntu/macos/windows + coverage gate.
- `release.yml` (tag `v*`): build matrix for the 5 targets
  (`x86_64/aarch64-unknown-linux-musl`, `x86_64/aarch64-apple-darwin`,
  `x86_64-pc-windows-msvc`), package `agentic-<arch>-<os>.tar.gz|zip`,
  `SHA256SUMS`, create GitHub Release. Asset names must match
  `upgrade::release_asset_name()`.

## Task checklist

- [x] Cargo skeleton, CLI dispatch, usage text, exit codes
- [x] Embedded knowledge base (`kb.rs`), dev-checkout override
- [x] Theme/config/ui/logging
- [x] Markers + manifest + managed-file protection
- [x] copy_dir_contents, extensions, specialization assets
- [x] AGENTS.md/MEMORY.md generation, dest mapping
- [x] MCP registry/writers, context7, codex TOML editing
- [x] MemPalace optional integration
- [x] agent-model-mapper
- [x] Doctor smoke checks
- [x] self-install
- [x] upgrade via GitHub Releases + project re-sync
- [x] ratatui TUI wizard
- [x] Unit tests (97 passing)
- [x] Integration tests (`tests/cli.rs`)
- [x] Real-run blackbox e2e (`tests/e2e_blackbox.rs`, `make e2e`): fake agent
      binaries on PATH exercise doctor pass/timeout/failure/fatal paths,
      MemPalace setup/skip/timeout, replay, profiles, manifest hash integrity
- [x] Coverage 81.5% lines / 83.3% regions, gate via `make test-coverage`
- [x] Makefile rewrite (`build/test/e2e/test-coverage/lint/fmt/install` +
      preserved content tooling)
- [x] `install` bootstrap script rewrite (GitHub Releases binaries)
- [x] README/CHANGELOG/UPGRADE updates, version 0.7.0 (`Cargo.toml` is the
      version source; package.json kept in sync, enforced by
      `make check-version-sync` and the publish workflow)
- [x] CI workflows (`ci.yml`, `release.yml`)
- [x] Removed bash `agentic` and `tests/e2e/*.sh`; npm channel reworked:
      `bin/agentic.js` is a thin launcher downloading the release binary
      (version pinned to package.json, cache `~/.cache/agentic-npm/<version>`),
      published via `publish-npm.yml` on release publication
- [x] Final verification: `make lint test test-coverage release-build` green;
      release binary (6.5 MB) verified standalone with embedded knowledge base
