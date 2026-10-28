# Changelog

## v8.4.0

- New install option `--agents-md <generate|keep>` (default `generate`, the old behaviour). With `keep`, root
  `AGENTS.md` belongs to the project: agentic never writes, overwrites, moves, or deletes it, also on
  `agentic upgrade --force`. The generated guidance (root `AGENTS.md` text, a separator, then the usual generated
  content) goes to `.agent/AGENTS.md`, to a root `AGENTS.override.md` for Codex (Codex reads it instead of
  `AGENTS.md`). `.claude/CLAUDE.md` imports `@../.agent/AGENTS.md`. OpenCode 2.0.x ignores config `instructions`
  and `.opencode/AGENTS.md`, so a new plugin `.opencode/plugins/agentic-agents-md.ts` adds `.agent/AGENTS.md` to
  every request through the session `context` hook; keep mode installs it instead of `.opencode/AGENTS.md`, and
  `generate` removes it.
  `.agentic.json` saves `settings.agents_md`, so `install`, the TUI, and `upgrade` replay it. A `keep` install
  prints the generated paths to add to `.gitignore`. Teams can now commit only a short hand-written `AGENTS.md`.
  See [docs/agentic-reference.md](docs/agentic-reference.md#root-agentsmd-generate-or-keep) and
  [docs/company-rules.md](docs/company-rules.md#commit-only-a-short-agentsmd).

- `AGENTIC_SKIP_BINARY_UPGRADE=1`: `agentic upgrade` refreshes the project without querying GitHub releases.

## v8.3.0

- Company rules sources can hold company skills (`skills/<name>/**`) and workflows (`workflows/<id>.md`).
  `agentic install` and `agentic upgrade` write them where pack skills and workflows go on every selected host:
  `.agent/skills`, `.claude/skills`, `.agents/skills`, `.opencode/skills`, `.agent/workflows`,
  `.opencode/commands`, and a `.claude/commands/<id>.md` wrapper. A company skill or workflow replaces the pack
  one with the same name. `AGENTS.md` lists them with their `description:`. Before, install read every `*.md` of a source as a rule, so a `SKILL.md` or a workflow
  became a company rule. See [docs/company-rules.md](docs/company-rules.md#company-skills-and-workflows).

## v8.2.0

- `agentic upgrade` no longer fails with `Symlink project path` when the current directory holds a host directory
  with internal symlinks, for example `~/.codex/packages/app-server-daemon/current` in the home directory. The
  project inventory now skips nested symlinks. A symlinked top-level agentic path, such as `.agent`, is still
  rejected.

## v8.1.2

- A pushed `vX.Y.Z` tag now also publishes the npm package: `release.yml` calls `publish-npm.yml` after it creates
  the GitHub release. Before, a release created with `GITHUB_TOKEN` did not start the `release` trigger, so npm
  stayed at 2.1.0 while GitHub had v2.1.1–v8.1.1. The publish step skips a version that is already on npm.

## v8.1.1

- README: describes the current product. Rules are the base, the quality gate checks and records acceptance, and
  lean (main session + `explorer`) is the default; `--profile team` is optional. New sections on guardrails,
  company rules, the artifact standard and the review regulation. "Honest numbers" shows benchmark round 6.
  Catalog numbers come from the tree: 16 specializations, 64 rules, 14 skills, 10 workflows.
- `images/coverage_scorecard.png`: rendered again from the current catalog, `reports/area-quality.json`, the
  always-on budget and benchmark round 6 (`reports/bench-round6.json`). `scripts/render_coverage_scorecard.py`
  reads these sources and no longer counts the specialization template.
- `images/how_to_use_agentic.gif`: recorded again with the current TUI (lean profile per host, "Company rules"
  step). `scripts/generate_how_to_use_agentic_gif.py` follows the new TUI steps and asks the native main session
  of each host instead of the `product-owner` role.
- `docs/agentic-reference.md` explains how to regenerate both README images. `reports/area-quality.*` is
  refreshed for the 16 current specializations.

## v8.1.0

- Docs site: the menu groups each specialization into Rules, Workflows and Skills. Workflow pages show use when /
  avoid when, inputs and outputs, numbered steps (Do / Done when), checks, artifacts, and links to rules and
  skills. Rule pages show where the rule applies (`paths:` or manual). The site no longer prints empty sections
  such as "Quality gates —", which appeared after the content cleanup.
- Docs site search covers rules, skills and workflows. The Mermaid diagram code and its CDN are removed; `marked`
  and `lunr` are pinned.
- `docs/site/catalog.json` 1.4.0 adds rules, skills and the specialization summary, and per workflow
  `avoid_when`, `checks`, `artifacts`, `steps`, `rule_refs` and `body`; it drops `roles`, `quality_gates` and
  `workflow_diagram`. `build_docs_catalog.py --validate` checks steps, rule scope and links to unknown rules or
  skills.
- `check-docs-coverage` no longer asks for a docs change when `Cargo.toml` or `package.json` changes only its
  version line (`version_files`; regulation DOC-5).

## v8.0.0

- Company rules: `agentic install --company-rules-path <dir>` and `--company-rules-git <url>[#ref][:subdir]`
  (repeatable; TUI step "Company rules") install rule files into `.agent/company/` for every host and
  `.claude/rules/company-*.md` for Claude Code. `.agentic.json` `settings.company_rules` stores the sources and
  `agentic upgrade` replays them (`docs/company-rules.md`).
- `--company-rules-exclude <area>/<spec>/<rule>` and `replaces:` in a company rule drop the pack rule; a later
  install or upgrade removes the copy it wrote if you did not edit it.
- Git sources are fetched shallowly into `~/.cache/agentic/company/` without credential prompts. Offline, agentic
  uses the cached copy, or keeps the installed files, with a warning. Credentials in URLs are hidden in output.
- With company rules, `AGENTS.md` gets one line: company rules in `.agent/company/` override agent-guides rules on
  conflict.
- After install and upgrade, agentic prints the pack rules that company rules duplicate (ART-K1/K2, needs
  `python3` 3.11+) with a `--company-rules-exclude` suggestion. It never fails the install.

## v7.0.0

- Breaking: the `lean` profile installs only the `explorer` helper. Benchmark round 6 rule H4: without `reviewer`
  lean accepted the same cells (T8v2: Codex 9/9 vs 9/9, Claude 3/3 vs 3/3) and the reviewer never ran there.
  `agentic upgrade` removes unchanged reviewer files and keeps edited ones; an unedited old `lean/profile.json`
  seed follows the new default. To keep the reviewer, add `"reviewer"` to a custom profile (`UPGRADE.md`).
- The core `AGENTS.md` asks for a reviewer subagent after a multi-module diff only when one is available
  (host-native or installed); the Claude lean command wrapper no longer starts `reviewer`.
- Benchmark round 6 (`docs/agentic-v2-lean/results.md`): H0 met on Codex (every lean helper ran on the session
  model; lean + JEV costs 1.09 × lean), H4 applied, H-clean partly met (quality kept; on the devops task T11 plain
  0/3 vs lean 3/3, lean uncached tokens ×0.72 and cost ×0.85 after the content cleanup).
- Benchmark: harder T8 (two code paths), new devops task T11 with its own install selection (`areas`,
  `specializations`, `fixture` per task), T10 graded on the Makefile targets every rule version requires, selftest
  negatives (`tests/bench/negative/`), `Accepted by gate` and `Released` report columns, mode `lean-noreviewer`
  (now an alias of `lean`).
- Codex `gpt-6.1-terra` is the `balanced` tier, the team role default and the benchmark coordinator default; it
  needs codex-cli 0.164 or later (0.153 rejects it with `model_not_found`). `tests/bench/prices.json` lists it at an
  estimated price.

## v6.0.0

- Breaking: the pack follows `docs/artifact-standard.md`; `make check-artifacts` runs with an empty baseline.
  86 rules, 98 skills, 73 workflows and 73 prompts became 64 rules, 14 skills, 10 workflows and no prompts.
  Installed content for `devops.infrastructure,devops.observability,software.backend,software.general` fell from
  about 69k to 14k tokens; every selection's always-on context is under 4,000 tokens on every host (Claude:
  infrastructure + kubernetes + sre 9,273 → 1,872).
- Breaking: removed the specializations `software.full-stack` and `software.platform`. `install` and `upgrade`
  map them to `software.backend` + `software.frontend` + `software.general` and to `devops.kubernetes` +
  `devops.infrastructure` + `devops.ci-cd`, with a warning. An unknown specialization now stops with the list of
  available ones.
- Breaking: ten role-neutral workflows remain: `develop-feature` (general), `debug-issue`, `refactor-module`,
  `code-review-workflow`, `add-migration`, `incident-response`, `debug-workload`, `iac-change`,
  `release-pipeline`, `security-scan`. Each has 4–5 steps with **Do** / **Done when** and an `Example request:`.
  Lean runs the steps itself; team sends each step to the installed role agent that fits it.
- Breaking: `agentic` no longer installs `prompts/`; an upgrade removes unchanged prompt files. The docs site takes
  examples from workflow `Example request:` lines (catalog 1.3.0).
- Breaking: `agentic upgrade` in a project with agentic files but no `.agentic.json` stops and asks for
  `agentic install` (or `agentic tui`); `--force` keeps the old default rebuild.
- Every rule has `paths:` or `trigger: manual` and lists checkable items. New backend rules `api-contracts`,
  `configuration`, `service-telemetry`; infrastructure rule `ansible-standards`; the image-digest item moved to the
  Kubernetes `workload-security` rule. Renamed and merged rules are listed in `UPGRADE.md`.
- `check-docs-coverage` counts a deleted file as covered by a changed page that covered it before.
- `scripts/sync_workflow_diagrams.py` and `make sync-diagrams` are removed.

## v5.0.0

- `make check-artifacts` (`scripts/check_artifacts.py`) checks rules, skills and workflows against every
  automatic requirement of `docs/artifact-standard.md`. It runs in `make lint-content` and CI with a committed
  baseline: only new findings fail (`--write-baseline`, `--strict-baseline`). Company terms for the leak check
  come from outside the repository (`AGENTIC_DENY_TERMS_FILE`). `--project <dir>` checks an installed project
  with its company rules (`--json`).
- `make check-docs-coverage BASE=<ref>` (`scripts/check_docs_coverage.py`) and a CI job on pull requests: changed
  code must be covered by a changed docs page (`covers:`), or every commit that touches it carries
  `Docs-Not-Needed: <reason>`. `--report-uncovered` lists code without a docs page.
- `scripts/context_budget.py --all-selections` measures the always-on budget for every specialization and the
  common multi-spec selections.
- Docs pages declare `covers:`. The authoring templates, `CONTRIBUTING.md` and `assess_area_quality.py` no longer
  require roles, quality gates or report files.
- The backend `database-safety` rule now lists only checkable items and no longer repeats the core line.

## v4.0.0

- `agentic install` and `agentic upgrade` warn when the checkout is older than origin's default branch: a branch
  with no own commits that is behind `origin/<default>`, or the default branch 20 or more commits behind. The
  check uses local refs only, never fetches or blocks, and suggests `git switch <default> && git pull`.
- The quality gate adds `--event start`: one line of session context for a stale checkout. Claude Code and Codex
  call it from a `SessionStart` hook; the OpenCode gate plugin uses the session `context` hook. Upgrades add the
  new hook group to existing installs; on Codex, trust it in `/hooks` (it needs codex-cli 0.153 or later).

## v3.0.0

- Quality gate: `.agentic/gate/last.json` records acceptance: `accepted`, `reason_code` (`checks_passed`,
  `checks_failed`, `max_blocks`, `no_changes`, `changelog_missing`), `head`, `pack_version`, `profile`. Old fields
  stay. A `max_blocks` release writes `last_release` to `state.json`; on Claude Code it shows
  `Agentic gate: NOT ACCEPTED (max_blocks)`.
- Production guard: before `kubectl`, `helm` or `oc` on a context that matches `guard.prod_context_pattern`
  (default `prod`, by flag or the current kubectl context), and before database clients on hosts in
  `guard.prod_hosts`, the gate asks the user. Custom `guard.confirm` rules (`{pattern, reason}`) add to the
  defaults; `guard.defaults: false` turns the defaults off. Claude Code and OpenCode ask; Codex hooks cannot ask,
  so on Codex the command is denied and the agent asks the user to run it.
- Database guard: the gate reads the Bash command, its heredocs, and the script files it runs. Write or
  maintenance SQL (`VACUUM`, standalone `ANALYZE`, DDL, DML, `GRANT`, `pg_terminate_backend`, …) against a
  non-local database is denied on every host; a connection that takes credentials from `.env` or the environment
  asks first; host plan mode denies any non-local database connection. Configure with `guard.db`
  (`mode: ask|deny|off`, `write: deny|ask`).
- The OpenCode gate plugin passes the agent, so the `plan` agent is treated as read-only.
- Breaking: gate hooks pass `--host`, so their commands change. After `agentic upgrade`, review and trust the
  changed Codex hooks in `/hooks`; until then Codex does not run them.
- Breaking: the production and database guards can ask for or block Bash commands that ran before (see
  `UPGRADE.md`).
- New backend rule `database-safety.md`; the core `AGENTS.md` adds one line: never run write or maintenance SQL
  on a non-local database, and ask before using database credentials from `.env`.

## v2.4.0

- JEV: in host plan mode (Claude Code `permission_mode: plan`, the OpenCode `plan` agent) the workflow hint is
  read-only: do only the diagnosis and analysis steps, present the rest as a plan, do not edit files. Codex is
  unchanged (its payload has no mode). The hint text lives only in the Python runtime.
- JEV (OpenCode): a code-mode MCP call that the host reports both as `execute` and as `<server>_<tool>` now gives
  one tool record under the concrete tool name, and the permission hook keeps that call's input.
- JEV (lean): `explorer` and `reviewer` spawns never route above the session model's tier (`balanced` when the
  session tier is unknown). When every candidate is above the cap, the result is `fallback/tier_above_session`
  and the helper runs on the session model.

## v2.3.1

- New `docs/artifact-standard.md`: the acceptance contract for rules, skills, workflows and company rules, with
  requirement ids (`ART-*`) and removal criteria. `CONTRIBUTING.md` links it.
- New `docs/regulation.md`: a vendor-neutral Definition of Done for code review (`CR-*`) and design review
  (`DR-*`, `IR-*`, `RD-*`), and the docs layout and code-to-docs coverage rule (`DOC-*`) for AI auditors.
- New rule `software/general/rules/docs-layout.md` (scoped to `docs/**`).
- The orchestration research adds anonymized field findings and the plan status; `docs/repo-scan-design.md` is
  now tracked.

## v2.3.0

- The benchmark price table and the docs no longer name a private OpenCode provider; they use the placeholder
  `private_llm`. The benchmark report matches a provider-prefixed model id to its price by the model part after
  `/`, and repo-scan `--provider litellm` strips any `<provider>/` prefix instead of one hardcoded name.
- repo-scan fixtures, tests and docs use neutral project names (`shared-lib`, `order-service`, `catalog-lib`,
  `example-group`).

## v2.2.0

- Release policy: every PR ships its own version, and `CHANGELOG.md` has no `Unreleased` section. A feature
  bumps MAJOR, a fix bumps MINOR, and docs, CI, or test-only changes bump PATCH (`docs/release-policy.md`). The
  installed `AGENTS.md` now tells agents to follow the project's release policy when it has one.
- The OpenCode doctor smoke check no longer fails with `missing required Authorization header`. OpenCode V2 keeps
  provider credentials in `opencode.db`, not in `auth.json`, so the isolated doctor home had none. The doctor now
  copies the credential tables (without sessions).
- The OpenCode doctor passes `--model`: `AGENTIC_DOCTOR_OPENCODE_MODEL` if set, else `model` from the project or
  global OpenCode config, else the model you used last (`recent[0]` in `state/opencode/model.json`). Without it,
  `opencode run` took the first model of whichever provider loaded first, so the check hit a
  different provider from run to run and sometimes failed on its quota (`HTTP 429`) or hung. The doctor also
  sets `OPENCODE_DISABLE_MODELS_FETCH=1` when `models.json` is cached, so startup does not wait for models.dev.
- The OpenCode doctor run is lighter and fits the default 10s timeout: it reuses your npm cache (`~/.npm`), so
  `npx` MCP servers are not downloaded again into the empty isolated HOME on every run, and it turns off the file
  watcher.
- Before each doctor run, `agentic install` and `agentic upgrade` remove leftover `$TMPDIR/agentic-*` directories.
  They first stop the processes still running there and delete the Codex, OpenCode, and Claude Code sessions that
  ran in those directories, so temp runs no longer pile up in the agents' session lists. The directory of the
  target project is kept.
- After the smoke checks, the doctor stops processes left in its temp root. MCP servers such as `anydb-mcp`
  outlived OpenCode and kept writing logs there.

## v2.1.2

- `agentic upgrade` adopts a gate hook group that is identical to the one it writes when the ownership record is
  missing. Upgrades with v2.1.0 lost `.agentic/codex-gate-hook-entries.json` and
  `.agentic/claude-gate-hook-entries.json`, so later upgrades warned `Preserving conflicting Gate hook entry`.
  A user-edited group is still left alone.

## v2.1.1

- OpenCode model profiles saved by older releases no longer bring back `telegram-notification` and
  `agent-model-mapper` in the `opencode.json` `plugin` array. OpenCode V2 tried to install them from npm and
  reported `Plugin failed: telegram-notification`.
- `agentic upgrade` skips `node_modules` in agent directories. OpenCode installs plugin dependencies there, and
  their `.bin` symlinks stopped the upgrade with `Symlink project path`.
- OpenCode model profiles saved by older releases no longer bring back the pre-1.4 role names (`designer`,
  `instruction_reviewer`, `memory_curator`); under `lean` they appeared as extra OpenCode agents.
- Quality gate: install and upgrade record `.agentic/gate/baseline.json`, the hashes of the files uncommitted at
  that moment. The Stop gate ignores files that still match, so the uncommitted installed artifacts no longer
  make it run `make test` after a session that only read code.
- `agentic upgrade` keeps the gate hook ownership records (`.agentic/claude-gate-hook-entries.json`,
  `.agentic/codex-gate-hook-entries.json`) in its staging copy, so it no longer warns
  `Preserving conflicting Gate hook entry` about its own hooks.
- A first install into a project without `.agentic.json` moves the agentic-marked files it no longer installs
  (for example the role team of an older install) into `.agentic-backups/<stamp>-legacy/`. Configurations stay.
- Claude Code doctor passes `--verbose`, which `--print` with `stream-json` output requires. The doctor's error
  patterns match within one phrase, so long JSON event lines no longer count as integration errors.
- OpenCode doctor works with OpenCode V2: it runs `opencode run --standalone --auto` in the project copy instead of
  the removed `--pure` and `--dir` flags.

## v2.1.0

- repo-scan `run`: scan and LLM assessment in one command. Focus mode (`--focus`, or a repository given as the
  root) scans context roots (`--context-root`, `REPO_SCAN_CONTEXT_ROOTS`, `~/.config/agentic/repo-scan.json`, else
  the `<host>/<group>` above the repository) so the links of one repository resolve, and reports only its view.
- repo-scan skill: `tools/repo-scan/skill/repo-scan` (`SKILL.md` and `scripts/repo-scan.sh`) runs both stages or
  one, for one repository or many; `make repo-scan-skill` installs it into `~/.claude/skills`.
- repo-scan requirements: `make repo-scan-check` (plain `sh`) checks `python3` >= 3.11 and `git`, prints the install
  command for the OS, and on a terminal offers to install a missing `scc`; `make repo-scan` runs it first.
  `make repo-scan-tools` installs `scc` (pinned release, checksum verified) and, on request, `semgrep`.
- Release policy: docs/release-policy.md says when to bump MAJOR, MINOR, and PATCH.
- Removed the stale `error.txt` CI log.
- Role profiles per host: `~/.config/agentic/<claude|codex|opencode>/profiles/<id>/profile.json` with `base`
  (`lean`/`team`), `agents` (the role files to install), and `models` (a model profile id). `lean/` and `team/`
  are seeded and never overwritten. The TUI asks for a role profile per selected host. New
  `agentic profile list|show|use|create`; `use` reinstalls through the upgrade path, removes unmodified old role
  files, and saves `settings.profile_ids` in `.agentic.json`. Custom profiles are also copied to
  `settings.profile_defs`, so a sync or upgrade keeps the same roles when the user file is missing. `--profile` accepts custom ids and
  `claude=team,codex=lean`. New `/profile` command for Claude Code and OpenCode and the Codex skill
  `agentic-profile`. Model profile menus now read `models: <provider> · role→model`.
- `tools/repo-scan`: offline analysis of many local Git repositories (Python standard library; `scc` when present).
  Repositories are identified by GitLab URL in every output, inferred from `~/work/<host>/<path>` or set per root
  with `--root-url <dir>=<url>`; the local path stays only in `repositories.json` for later stages.
  `scan` writes `repositories.json` (URL checked against `origin`, activity class
  active/stale/docs/archived/junk, languages, Makefile, CI, manifests, env keys and hosts only), `relationships.json`
  (`library`, `http`, `kafka`, `grpc`, `ci`, `deploy` edges with evidence, confidence and a `trusted` flag at
  `--trusted-min`, default 0.8; unresolved links are listed, not guessed), `guide-applicability.json` (declarative rules in `tools/repo-scan/applicability.json` with
  real workflow and rule ids, separate task routing hints) and `graph.mmd`. `--write-repo-artifacts` writes
  `.agentic/` files into each repository and git-excludes them. `gate-propose` builds `.agent/gate.json` candidates
  without running code; `gate-verify` runs them only in named repositories. `llm` adds an assessment through
  `claude -p` or an OpenAI-compatible LiteLLM endpoint, cached by HEAD sha. New targets `make repo-scan` and
  `make test-repo-scan` (part of `make test`). See docs/repo-scan.md.
- Lean + JEV: JEV no longer forces the `team` profile. With `--profile lean` (the default), JEV makes one
  workflow call per session and adds a short checklist hint for the chosen workflow. The native main session
  performs the steps and starts subagents only where the core rules ask; spawn hooks still route the models of
  `explorer`, `reviewer`, and native agents. A `native` answer adds no context. Lean keeps the Codex thread
  default and the helpers' reasoning effort. `team` + JEV is unchanged, and projects that saved `team`, or
  that have JEV but no saved profile, stay on `team`. A new `--enable-jev` install without `--profile` is now `lean`.
- SDLC benchmark: arms `lean-jev`, `team`, and `team-jev`; `--reps` with a seeded random order; one stable
  project per host and arm (Codex trusts hooks per path), with a copy per cell for regrading; host crashes
  and missing JEV records count as `harness_error`, not as failures; output tokens, API-equivalent cost from
  `tests/bench/prices.json`, cost per accepted task, Wilson intervals, and `summary.json`. New tasks T6
  (multi-module bugfix) and T7 (multi-module feature with an all-or-nothing edge case). `--effort codex=<level>`
  sets the Codex coordinator effort. OpenCode JEV routing stays on the coordinator's provider, so one cell never
  mixes providers. A routed model without a price leaves the cost empty instead of borrowing the coordinator's price.
- Benchmark round 4 (252 cells, 3 reps, docs/agentic-v2-lean/results.md): Lean + JEV matches lean on success,
  costs 1.02 × lean per accepted task on Claude, 1.12 × on OpenCode, and 1.43 × on Codex, where JEV routed helper
  spawns to a frontier model. It stays opt-in; no savings are claimed.
- README tagline: native agents by default; workflows, helper agents and model routing only when the task needs them.
- Docs: orchestration research (docs/agentic-orchestration-research/): mechanism map, measured loss sources from
  round 4 raw cells, host constraints, target architecture, prioritized plan, and comparison designs.

## v2.0.0

Breaking: the default install is now the `lean` profile. See UPGRADE.md, "Migrating to v2.0.0".

- Always-on context drops by about 84% per host (backend + general: Claude 12.2k → 1.9k, Codex 9.4k → 1.5k, OpenCode 10.8k → 1.8k estimated tokens). The root `AGENTS.md` becomes a short core: load on demand, scale the process to the task, an evidence-based definition of done, and git basics. The core reads a rule or skill only when the task touches its subject, forbids an explorer subagent (ours or the host's native one) for code you can list with one command, and bumps the version only for a completed feature; a bugfix updates `CHANGELOG.md` only.
- General and backend rules are path-scoped (`paths:`) or `trigger: manual`. `.claude/rules/` gets only always-on and scoped rules. Spec `AGENTS.md` files no longer list rules; the workflows and skills that need a rule link it.
- New `--profile lean|team`. `lean` (default) installs only the `explorer` and `reviewer` subagents and keeps the native main session. `team` keeps the v1 role team; JEV always uses `team`.
- New quality gate, on by default (`--disable-gate` to remove): a Stop hook runs `make test`/`make lint` when files changed and asks once for a CHANGELOG entry; a PreToolUse guard denies secret files, force pushes, and recursive deletes outside the project. One runtime (`.agent/gate/gate.py`) serves Claude Code, Codex, and OpenCode (plugin).
- Codex skills install to `.agents/skills`, where Codex discovers them. The Codex "always use a subagent" override installs only in `team`.
- Installed workflows drop the generated mermaid diagram. `develop-feature` and Claude command wrappers delegate per role only in `team`.
- New measurement tools: `make context-budget` (offline always-on estimate) and an SDLC benchmark (`make bench*`: plain vs v1 vs lean, five graded tasks including the red-lint trap T5, self-tested graders; the report shows full input tokens next to uncached). Results: docs/agentic-v2-lean/.
- Install on Windows: rule front matter and workflow diagrams parse from CRLF checkouts, so manual rules no longer land in `.claude/rules/`.
- Upgrade on Windows: manifest-owned files in nested folders (for example `.agent/workflows/*.md`) are no longer treated as user files, so a sync no longer removes and recreates them.
- Operational: Codex requires `/hooks` trust for the new gate hooks in each project.
- Benchmark, pilot, and blackbox scripts no longer pass `--no-daemon` to Codex; Codex CLI 0.153 rejects the flag.
- Codex in `lean`: Codex memories stay off (they added about 1.8k tokens of cross-project memory to every request; `team` keeps them), and the `explorer` and `reviewer` agents inherit the session model instead of pinning models the account may not serve.
- The core asks for a reviewer subagent only after a diff that spans several modules; a feature in one module needs none.

## v1.6.0

- Shell permission operands resolve from the actual cwd; unknown cwd retains native approval. Preserve secret, symlink and allowed-root boundaries.
- Capability tiers come from explicit maps and candidate-validated overrides, never price rank; unknown costs remain unknown. Pins, provider filters and role-default fallback stay in force.
- Existing `jev on` is an explicit new-task boundary. Task generations isolate cached decisions, approval history, prepared spawns and review packets; late answers cannot restore a reset task. Cached allow rechecks path boundaries.
- Codex gains a local `--prepare-spawn` interface using open goal/scope/complexity before encryption, with idempotent expiring decisions and separate recommended/submitted/observed evidence. The response has one callable `spawn` object (`agent_type`, `jev_<hex>` task name, model unless pinned, `fork_turns=none`), so restricted profiles keep their policy and still correlate. A denied ticket falls back once to native role defaults and is logged as `recommendation_discarded`. Child observations bind through the host transcript of the exact thread. List-valued metadata is joined; wrong types return `prepared_metadata_invalid`. Live native proof: recommended, submitted and observed model matched.
- REVIEW_PIPELINE adds per-agent/model token tables, provenance, partial totals and separate JEV usage; manual acceptance remains last. No savings are inferred.
- Comparative pilot (39 cells, 3 hosts): plain agents were cheapest on small tasks; see docs/jev-integration/epic/pilot_results.md. New tools: `scripts/pilot_jev.py`, `scripts/render_coverage_scorecard.py`, a real-TUI `scripts/generate_how_to_use_agentic_gif.py`.
- README rewritten for a non-specialist audience; technical details moved to docs/agentic-reference.md.
- Candidate release: not yet published. Re-run upgrade to install the updated runtime; coordinators must start a new task after upgrade so the new spawn contract is injected. See docs/jev-integration/epic/.

## v1.5.0

JEV now decides once per session and spends fewer calls; review reports end with manual acceptance commands. Requirements: `docs/jev-integration/session-gate/README.md`.

- JEV session gate (all hosts). Only the first root prompt of a session asks the workflow question. A selected workflow keeps JEV on; `native`, low confidence or an error turns JEV off for the rest of the session (`session_off`); `clarify` asks again on the next prompt. Later prompts make no call and stay bound to the first task (`session_follow_up`), so answers such as «да» or «как отработал JEV» no longer open a new task or move spawns and review packets to it. A later prompt that names a workflow (`/develop-feature`) starts a new task without a call. In an off session, spawns still get the role default without a call.
- Manual switch: `/jev off`, `/jev on`, `/jev status` per session, with no JEV call. Install adds `.claude/commands/jev.md` and `.opencode/commands/jev.md`; in Codex type `jev off` if the TUI rejects the slash command. Claude Code and Codex hooks block the switch prompt, so it costs no model turn; OpenCode answers with one line. `/jev on` restarts workflow selection.
- Model threshold default is now 0.6 (workflow and permission stay 0.9). Below it, the role default from the installed profile applies.
- Claude in an install with Codex: `model-defaults.json` gains `hosts.claude` with the Claude profile roles and tiers. Before, the Codex ids gave Claude no alias, and low-confidence spawns inherited the coordinator's model (often opus).
- Removed fields that were always empty: `usage.cost_usd` (records now keep `input_tokens` and `output_tokens`), observation `requested_model`, and the `AGENTIC_JEV_BUDGET_FILE` ledger that booked a fixed $0.02 guess per call.
- Blackbox: the prompt is «разработай простой калькулятор на Python в одном файле», at most three prompts and 8 minutes per host (was 20 minutes), and a new `follow_up_without_jev_call` check. `results.json` reports `jev_calls`, `jev_input_tokens` and `follow_up_prompts` instead of `jev_reported_cost_usd`.
- Post-task review: `summary.md` and the final response end with a `Manual acceptance` section: copy-paste commands from the project root, the expected result of each, manual steps and cleanup. Commands not run during delivery are marked `not run`.
- Migration: reinstall the target project to get the new runtime, `hosts.claude` and the `jev.md` commands. Hook entries are unchanged, so Codex needs no new `/hooks` review. Remove `AGENTIC_JEV_BUDGET_FILE` from local scripts. Custom `settings.jev.thresholds.model` values are kept; remove them to use the new 0.6 default. Old `context-*.json` files without `jev` count as on.

## v1.4.1

Bug-fix release for 1.4.0. It fixes the JEV questions, which caused most JEV fallbacks, and the Telegram "done" mark.

- JEV questions rework (all hosts). In the reference run only 2 of 11 answers were applied; the questions caused most fallbacks.
  - Workflow question: options come from `type: workflow` files and show description, inputs → outputs, roles and the new `selection.use-when`; the general workflow is marked `GENERAL.`. New options `native` (`fallback/native_request`) and `clarify` (`fallback/clarification_needed`) keep native behaviour. State has the original request, installed areas and a bounded repository snapshot instead of the catalog.
  - Model question: JEV picks a tier (`fast` / `balanced` / `frontier` / `clarify`) for the assignment; the hook maps it to a model (Claude haiku/sonnet/opus, Codex `extensions/codex/model-tiers.json`, OpenCode by catalog price). The session model is no longer sent or used. `clarify`, low confidence, an API error or `no_tier_routing` apply the role default on Codex, OpenCode and Claude (`model_source: role_default`, was `profile_default`).
  - Permission question: asked only for requests inside the automatic boundary; others are not sent to JEV (`not_auto_allow_eligible`, native host decision). State has path and command metadata only (no file content, no full command, no outside path: `[outside project]`, `secret_like`), the requesting role when it is installed, and the last 10 applied decisions.
  - Redaction no longer corrupts identifiers such as `tests_and_review_evidence`, `parts_inventory_service` or `task-ask-me`: token patterns match only at a token start. `ts_` tokens need a digit; `sk-` (including `sk-proj-`, `sk-ant-`) and `jv_live_` tokens need a digit or 20+ characters. GitHub (`ghp_`…), AWS access key ids (`AKIA`…) and Slack (`xox?-`) tokens are now redacted too.
  - Spawn records label agents like observations: an installed role in `agent`, otherwise `agent: null` and `native_agent_type`. `scripts/blackbox_jev.py` pairs spawns and observations by either label, so native helpers such as `Explore` count.
  - Instructions no longer contain test-case wording. Requests are sent as UTF-8; a Cyrillic prompt no longer inflates the 32 KiB budget about six times.
  - New `settings.jev.thresholds.{workflow,model,permission}` (valid range 0.5–1, default 0.9). Reinstall keeps `thresholds`, `lightweight_model` and `tiers`.
  - Audit records gain `decision`, `threshold`, `applied`, `outcome`, and for spawns `tier` and `model_source`. Observations of non-role subagents (for example `Explore`) have `agent: null`.
  - The runtime is split into `hook.py`, `questions.py`, `routing.py`, `adapters.py` and `api.py`; all are installed to `.agent/jev/`. A partial runtime (including a missing `api.py`) falls back with `runtime_incomplete` and writes an identifier-only record.
  - OpenCode model routing now works without catalog prices (OpenAI oauth reports `cost: []`). A shipped tier map, installed as `.agent/jev/opencode-model-tiers.json`, gives `openai/gpt-6-luna` / `openai/gpt-6.1-sol` / `openai/gpt-6-astra`, filtered to the host catalog and to one provider (`cost_source: tier_map`); a role default on a provider without a map entry gets no map tiers. Complete, distinct prices still win (`catalog_price`). The plugin adds the map models to the spawn pool.
  - OpenCode role defaults are resolved in the hook: a profile model in the catalog wins (`role_default_source: profile`); otherwise the role's tier from the map applies (`role_tier`; `balanced` for product-owner, team-lead, developer, devops-engineer; `fast` for qa, analyst, pm and the reviewers). A default install therefore gets a role default for every installed role. Spawn records gain `cost_source` and `role_default_source`.
  - `instruction-reviewer` without prices or a lightweight model gets the `fast` tier (`tier_fast_price_unknown`).
  - Codex: a spawn with an encrypted assignment is no longer sent to JEV; it gets `fallback/assignment_unavailable` and the role default (every such call had answered `clarify`). The Codex `qa` default is now `gpt-6-luna` (`fast`; `gpt-6-terra` is not in the Codex catalog).
  - The OpenCode `openai` profile now uses only catalog ids with the `openai/` prefix: `developer` → `openai/gpt-6.1-sol`, fallbacks `openai/gpt-6-astra`, `small_model` → `openai/gpt-6-luna`. A content test checks shipped ids against frozen host catalogs.
  - `scripts/blackbox_jev.py` resolves `--run-dir` to an absolute path.
- Migration: `.agent/jev/model-defaults.json` is now `{"version": 2, "roles": {...}, "tiers": {...}}`; reinstall rewrites it, and the hook still reads the old flat file (roles only, no tier routing). Every `areas/**/workflows/*.md` needs a `selection` block (`make lint-content` enforces it); see `CONTRIBUTING.md`. Old `event-*.json` records stay valid; new records use a versioned identity, so an event is not served from a pre-rework record.
- Operational (OpenCode JEV): reinstall to get `.agent/jev/opencode-model-tiers.json`; without it the hook keeps the price-only behaviour. Users with a custom OpenCode profile keep their explicit catalog models as role defaults; a profile model that is not in the catalog is replaced by the role's tier model. Restart OpenCode after the reinstall: the plugin reads the tier map once, at setup.
- Telegram header (all hosts): a second line `🤖 <agent> · <model>` names the main-session agent and the model of the last answer, from local host data. `✅ Задача завершена` is now sent once, on the final turn: the coordinator's turns that leave subagents or background tasks running become `💬 Промежуточный ответ`. When the evidence is unclear, the turn is interim. The new helper `.agent/notify/telegram_turn.py` is installed and removed with `telegram.py`; reinstall to get it (without it, every message is interim). The transcript scan runs only in the detached sender. See `docs/notifications`.

## v1.4.0

- Claude Code now matches OpenCode and Codex. Install writes `.claude/rules`, `.claude/skills`, one `.claude/commands/<workflow>.md` wrapper per workflow, `.claude/CLAUDE.md` with `@AGENTS.md` and `@MEMORY.md` imports, and an ownership-tracked `.claude/settings.json` (`agent: product-owner`, approved `.mcp.json` servers, hooks).
- Claude model profiles: the default `anthropic` profile pins `opus`, `sonnet` or `haiku` per role. Use `--claude-profile none` to inherit the session model. Role agents now declare `tools:`, and both post-task reviewers are read-only.
- JEV native hooks for Claude Code: workflow context, alias-only model routing through the Agent tool, permission decisions, and the reviewer packet. See `docs/jev-integration`.
- Fixed Claude JEV model routing: subagent hand-backs and task notifications no longer replace the original request (before, most spawns after the first fell back to the session model). `AskUserQuestion` and `ExitPlanMode` are no longer sent to JEV as permissions. The session model is now read from the transcript and settings instead of an assumed `sonnet`. Without a confident JEV answer, a Claude subagent now gets its role's model from the Claude profile (for example `developer` → `sonnet`) instead of inheriting the session model, which was often `opus`.
- Telegram notifications for Claude Code and Codex through native hooks (`Stop`, plus waiting-for-input events), using one shared runtime, `.agent/notify/telegram.py`. New flags: `--enable-telegram` and `--disable-telegram`. Credentials stay in `~/.config/agentic/config.json`. See `docs/notifications`.
- OpenCode Telegram plugin rewritten for the OpenCode V2 plugin API (V2 did not load the old plugin). It now also reports waiting for input (`permission.asked`, `question.asked`), skips subagent sessions, and sends through the shared runtime.
- Telegram messages on all hosts render agent Markdown as Telegram HTML (code, bold, links, lists, tables as monospace blocks) and fall back to plain text when Telegram rejects the markup. The header names the project and host; the `📊 +0 -0` line is gone.
- Upgrade removes `telegram-notification` and `agent-model-mapper` from the `opencode.json` `plugin` array: they are local plugins, and OpenCode V2 tried to install them from npm (404).
- SDLC roster on all hosts: product-owner → team-lead → developer → qa → optional devops-engineer → post-task review. `pm` and `analyst` are optional. OpenCode `permission.task` now allows devops-engineer, and allows the reviewers from every coordinator. The reviewers are denied edit and bash.
- **Role renames (migration):** `designer` → `analyst` (system analyst), `instruction_reviewer` → `instruction-reviewer`, `memory_curator` → `memory-curator`. Install and upgrade remove unmodified old role files and old OpenCode role keys. Edited files are kept, with a warning. The JEV runtime accepts both spellings.
- All 98 skills now carry valid `name` and `description` frontmatter, and `lint_prompts.py --strict` enforces it. Added `make blackbox-claude`, which runs a real Claude CLI with JEV, a fake Telegram API, and checks that agents, commands, skills and rules load. Added `make test-notify`.
- Blackbox: one bounded approval follow-up on every host, Telegram check on every host, `BLACKBOX_CODEX_SANDBOX` for hosts that block bubblewrap, OpenCode default model `openai/gpt-6-luna`, and operator-spelling dialects in the calculator probe.
- Operational: Python 3.10+ is required when JEV or Telegram is enabled (the OpenCode plugin now calls Python too). Codex Telegram hooks need a `/hooks` trust review.

## v1.3.0

- Added opt-in JEV native hooks for Codex and OpenCode V2 (2.0.28+), replacing the shared skill and workflow-specific checkpoints. Hooks select an installed workflow and an available subagent model; explicit user selections remain authoritative.
- Preserved TUI activation and masked key entry. The official TypeSafe AI server remains the default, with CLI/environment overrides for the paid test gateway.
- Permission hooks retain sandbox restrictions and native denials. Sensitive or unbounded operations require normal user approval; failures and low-confidence responses fall back to native behavior.
- Local cleansed JEV Q/A and routing evidence are retained for 30 days and included in the existing advisory review pipeline. Unknown prices or application evidence are reported explicitly.
- Added opt-in `make blackbox` checks with real local Codex/OpenCode and the calculator prompt; ordinary tests and CI do not make paid requests. Codex requires native hook trust review.
- Install/upgrade now ignore `.agentic*/` and `.review*/` directories without ignoring `.agentic.json`. Existing local review artifacts are no longer tracked.
- Fixed Windows knowledge-base path normalization for Codex model routing; bundled model defaults remain open when JEV is enabled, while user pins and explicit agent limits are preserved.
- Limited JEV model candidates to project role defaults intersected with the host catalog. Hook sources now live under each environment's `extensions/<host>/hooks/` directory.
- Root guidance requires customer approval for new repository-root files and uses an approximate 80% simplified technical writing target, preserving precision for complex material.

## v1.2.0

- Upgrade now synchronizes using the newly installed executable and supports an explicit project directory.
- Smart project upgrades adopt recognizable legacy artifacts, merge local guidance edits using generated baselines, and back up conflicts before replacing them. Fully user-owned instructions are preserved with a manual-integration report.
- Added `upgrade --force` to rebuild recognized Agentic artifacts without prompts, replaying manifest settings or falling back to `default + software.general` with optional integrations off.
- Project updates are staged, backed up privately under `.agentic-backups/`, and restored on application failures. Shared configurations retain unrelated fields; global settings are preserved.
- Manifest v2 remains compatible with v1. The first upgrade of customized v1 instructions without a baseline replaces them with backup. Exclude backups from source control; they can contain project credentials.
- Fixed Windows release ZIP extraction and added executable validation before binary replacement.

## v1.1.0

- Added automatic, compact instruction and documentation/memory reviews after successful top-level delivery in six core SDLC workflows, across Claude, Codex, OpenCode, and existing Gemini profiles.
- Installed a shared on-demand REVIEW_PIPELINE.md protocol with read-only specialists, advisory recommendations, bounded evidence/searches, and non-blocking failure reporting.
- Preserved user-modified managed guidance on upgrades; review hooks or profiles skipped by managed-file protection must be reconciled manually. No memory migration or automatic recommendation application is performed.

## v1.0.0

- Persisted Context7 API-key mode in project manifests so upgrades do not repeat interactive prompts.
- Applied a 30-second default timeout to MemPalace operations, including upgrade graph refresh.
- Removed the obsolete `--install-fzf` option and its report output.
- Fixed the bootstrap installer cleanup trap so successful installs exit with status 0 under Bash `set -u`.

## v0.7.0

- Rewrote the `agentic` CLI from Bash (5598 lines) to Rust: a single self-contained cross-platform binary with the knowledge base (`areas/`, `extensions/`, root guidance files) embedded at build time.
- Removed all runtime dependencies: `git`, `curl`, `jq`, `python3` (for core flows), `fzf`, `sed`/`awk`, and `shasum` are no longer required. `python3`/`pip` are checked only when the optional MemPalace integration is enabled.
- Replaced the fzf-based TUI with a fullscreen ratatui wizard preserving the exact linear flow: theme → project directory → agent OS multi-select → MCP servers (with `[x]` detection of already-configured servers) → areas → per-area specializations → install.
- `agentic upgrade` now downloads the latest release binary from GitHub Releases and atomically self-replaces, then re-syncs the managed project in the current directory (replay install + MemPalace graph refresh).
- New `install` bootstrap script downloads platform binaries (linux x86_64/aarch64 musl, macOS Intel/ARM) from GitHub Releases; Windows x86_64 binaries are published as zip assets.
- Preserved 100% of the install pipeline semantics: manifest idempotency, managed-file protection (unmanaged/user-modified/config skips), marker injection with `created_by` preservation, MCP registry and per-agent config writers, OpenCode plugins/profiles/agent-model-mapper, codex TOML editing, doctor smoke checks with fatal-pattern classification.
- Fixed an upstream validation bug: the documented `default` agent OS is now accepted by `--agent-os` validation.
- Reworked the npm distribution: `@jetrabbits/agentic` is now a thin Node launcher that downloads the platform binary for the matching release tag from GitHub Releases on first run (per-version cache in `~/.cache/agentic-npm/`); publishing runs on GitHub Release publication with a Cargo/npm/tag version-sync gate. Removed the bash e2e suite; testing is now `cargo test` (unit + integration + real-run blackbox e2e with fake agent binaries) with an enforced 80% line-coverage gate (`make test-coverage`).
- Added CI (`ci.yml`: fmt/clippy/tests on linux+macos+windows + coverage gate) and release automation (`release.yml`: 5-target build matrix publishing `agentic-<arch>-<os>` assets with SHA256SUMS).

## v0.6.3

- Added a top-level `agent` field to every workflow frontmatter, matching `execution.initiator`, and updated the workflow template to preserve the contract for newly created workflows.

## v0.6.2

- Simplified the static docs site header by removing the install command block and shortened sidebar workflow labels by dropping the leading slash from triggers.

## v0.6.1

- Improved the static docs site navigation with compact expandable devops/software sections, nested area menus, active workflow state, independent sidebar/content scrolling, and a full-width search field under the install command.

## v0.6.0

- Added area-level `AGENTS.md` indices for `areas/devops/` and `areas/software/` with spec selection, cross-cutting constraints, and a global workflow trigger registry.
- Renamed colliding workflow triggers: full-stack `/develop-feature` → `/develop-feature-fullstack`, full-stack `/debug-issue` → `/debug-issue-fullstack`, platform `/incident-response` → `/service-incident` (devops/sre keeps `/incident-response`; backend keeps `/develop-feature` and `/debug-issue`). Update any saved prompts that used the old full-stack/platform commands.
- Extended the workflow template contract: `devops-engineer` is now a standard role; every loop/retry must state a maximum iteration count and an escalation path; cross-workflow trigger chains must be acyclic or carry a circuit breaker; every workflow Exit ends with an explicit `Next: /trigger` or `Next: terminal` handoff.
- Bounded all previously unbounded fix/retest, review, and mitigation loops across devops and software workflows, and added circuit breakers to the backup-verify ↔ db-incident, crash-triage ↔ store-submission, smoke-test ↔ deploy-production, and mlops incident→retrain→redeploy cycles.
- Added the missing rollback failure path to `/secret-rotation` (previous credential retained until the new one is verified).
- Standardized completion contracts: delivery workflows end with docs + CHANGELOG + version updates; incident workflows file root causes at `docs/incidents/<date>-<slug>-root-cause.md` (replacing wiki/ticket/`.data`/`.mlops`/`.security` destinations).
- Normalized workflow role hygiene repo-wide: initiators declared in their own roles list, no undeclared or unused step roles, no parenthetical role annotations, and named handoff artifacts in step Inputs.
- Regenerated workflow diagrams, the docs site catalog, and area quality reports (net −102 quality warnings).

## v0.5.3
- Isolated install-time OpenCode doctor runs into a temporary XDG home so doctor no longer reuses or pollutes the user's persistent OpenCode session database.
- Extended doctor e2e coverage to assert isolated OpenCode HOME/XDG paths and prevent `opencode.db` leaks into the caller home.

## v0.5.2
- Updated Codex MCP config generation so selected network-backed MCPs enable project sandbox network access, use non-interactive `npx -y` startup, and include startup/tool timeouts for reliable first-run startup.
- Extended deterministic MCP and doctor e2e coverage for all selected Codex MCP entries.

## v0.5.1
- Moved OpenCode Telegram notification credentials to `$HOME/.config/agentic/config.json` and added interactive reuse of saved credentials.
- Kept project `.agentic.json` limited to Telegram enablement so project manifests no longer store raw Telegram secrets.

## v0.5.0
- Fixed skill and rule dependencies within workflows

## v0.4.0

- Fixed OpenCode MCP config generation to use top-level `mcp` entries and migrate/remove legacy `mcpServers` from generated OpenCode configs.
- Added readable OpenCode menu labels for Telegram notifications and agent model mapping while preserving existing internal ids.
- Added committed OpenCode model profiles for OpenAI and GitHub Copilot under `extensions/opencode/profiles`.
- Added OpenCode profile choices to the optional OpenCode menu with manifest persistence and MCP-safe config merging.
- Renamed generated Docker MCP server entries from `MCP_DOCKER` to `docker`.
- Added non-fatal local prerequisite warnings for selected Kubernetes and Docker MCP integrations.
- Removed the macOS bash 3.2 warning and added compatibility handling for older bash empty-array behavior.
- Extended deterministic e2e coverage for all-MCP doctor setup, OpenCode MCP migration, OpenCode profiles, readable menu labels, and bash 3 compatibility.

## v0.3.4

- Enabled Codex project memories by generating `.codex/config.toml` with `[features] memories = true` whenever Codex is selected.

## v0.3.3

- Updated MemPalace project initialization to pipe explicit confirmation (`echo "Y" | mempalace init ...`) for non-interactive setup robustness.
- Removed `agent-model-mapper` from OpenCode plugin registration.
- Deleted obsolete OpenCode plugin source `extensions/opencode/plugins/agent-model-mapper.ts`.

## v0.3.2

- Added optional post-task specialist agents `instruction_reviewer` and `memory_curator` outside the mandatory SDLC role matrix.
- Added review pipeline guidance, `.reviews/<task-id>/` output conventions, and documented example instruction/memory review reports.
- Registered the new specialists in OpenCode role configuration and extended deterministic install/model-mapper coverage.

## v0.3.1

- Added project-level OpenCode plugin settings in `.agentic.json`, including Telegram `botToken` and `chatId` when `telegram-notification` is enabled.
- Renamed the OpenCode optional plugin menu entry to `telegram-notification` while preserving the old `telegram-opencode-notifier` alias for compatibility.
- Changed `telegram-notification` runtime credentials to read from the target project's `.agentic.json` instead of Telegram environment variables.
- Removed Telegram message formatting entirely: notifications are sent as plain text without `parse_mode`, MarkdownV2 escaping, or markdown-to-Telegram conversion.
- Added interactive Context7 key mode selection with English menu entries for keyless setup or entering `CONTEXT7_API_KEY`.
- Removed the post-install Context7 "add API key later" path/example guidance because key selection now happens during setup.
- Extended `agent-model-mapper` model discovery to include active providers from `~/.local/share/opencode/auth.json` and non-deprecated models from `~/.cache/opencode/models.json`.
- Added a Confirm/Cancel save step after OpenCode role model selection before writing `.opencode/opencode.json`.
- Preserved OpenCode plugin settings across manifest replay/re-install so automated sync does not prompt again or lose project-level credentials.
- Updated OpenCode, Context7, Telegram, and lifecycle docs plus deterministic e2e coverage for the new configuration flow.

## v0.3.0

- Added per-agent doctor timeouts with elapsed-time and exit-status logging while keeping install non-fatal.
- Replaced the OpenCode model checker with `agent-model-mapper` for explicit role-to-model mapping.
- Moved `agent-model-mapper` prompts to install time so OpenCode startup stays non-blocking.
- Removed the interactive Context7 API-key prompt and made OpenCode MemPalace project initialization optional/manual.
- Changed Telegram notifications to read credentials from environment variables only and avoid logging secrets.
- Added traced shell coverage tooling with a 90% `agentic` line coverage gate.
- Added deterministic OpenCode plugin, Telegram, and doctor timeout continuation tests.
- Added real Codex, OpenCode, and Telegram blackbox scenarios to normal `make test`.

## v0.2.0

- Added `agentic --version` and version display in CLI/TUI output.
- Added post-install doctor smoke checks for selected real agent targets.
- Added timestamped install logging with a mirrored `/tmp/agentic-*` file.
- Added install/TUI runtime requirements checks for Python, pip, and managed-file hashing tools.
- Changed generated MemPalace MCP configs to call `mempalace-mcp` without arguments.
- Added opt-in real-agent doctor E2E coverage.
- Added version metadata for generated Agentic markers while preserving the GitHub repository link.
- Kept schema-sensitive agent configuration files free of Agentic marker metadata.
