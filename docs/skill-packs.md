---
covers:
  - src/skill_packs.rs
  - src/source.rs
  - src/company.rs
  - src/install.rs
  - src/manifest.rs
  - src/main.rs
  - src/app.rs
  - src/tui.rs
  - src/markers.rs
  - src/project_inventory.rs
  - src/pocock_setup.rs
  - src/github_stars.rs
  - src/project_transaction.rs
  - src/project_update.rs
  - src/util.rs
  - src/pocock_setup/*.md
  - src/agentsmd.rs
---

# Skill packs

Status: implemented. A skill pack is a set of ready-made skills in an external git repository or a local
directory, for example [mattpocock/skills](https://github.com/mattpocock/skills) (MIT). agentic installs the
skills of a pack into the skills directory of every selected host. agentic does not rewrite the skills. A
user-invoked skill gets a user entry point on every host ([Hosts](#hosts)).

## Purpose

- Use skills that other people maintain, with one command, on every host.
- Keep the install reproducible: the manifest locks the commit of a git pack.
- Remove a pack cleanly: agentic removes only the files that the pack installed.

The feature is opt-in. Without `settings.skill_packs` in `.agentic.json`, install and upgrade work as before.

## CLI

```bash
# Install with a pack (repeatable). The project gets .agentic.json.
agentic install --project-dir . --agent-os claude,codex,opencode --areas software \
  --specializations software.backend --skill-pack 'https://github.com/mattpocock/skills#main'

# Manage the packs of an installed project (default: the current directory).
agentic skills add https://github.com/mattpocock/skills --id mp --select tdd,grill-me
agentic skills add pocock --issue-tracker github   # the preset; see Presets
agentic skills add ./vendor/skills --skills-root . --exclude draft-skill
agentic skills list
agentic skills update            # every pack
agentic skills update pocock     # one pack
agentic skills remove pocock
```

| Command | Effect |
|---|---|
| `skills add <spec> [--id <id>] [--select a,b] [--exclude x,y] [--skills-root <dir>]` | Adds the pack, or replaces the pack with the same id. A pack with the same source and `skills_root` (for a preset: the same preset) keeps what the command does not set: `select` without `--select`, `exclude` without `--exclude`, the own `ref` of a preset, and the locked commit of the same ref. |
| `skills list` | Prints each pack: id, source, `ref`, locked commit, `select`, `exclude`, and the installed skill names. |
| `skills remove <id>` | Removes the pack from the settings and its files from the project. |
| `skills update [<id>]` | Resolves the `ref` again and installs the new commit. Without an id: every pack. |

Common options: `--project-dir <dir>`, `--dry-run`, `--no-doctor`. `add`, `remove`, and `update` need an
existing `.agentic.json`. They change `settings.skill_packs` and synchronize the project like `agentic upgrade`:
in a staging copy, with a backup in `.agentic-backups/`, and all or nothing.

`<spec>` is one of:

- A git spec `<url>[#ref][:skills_root]`: a URL with `://`, a `git@host:path` URL, or a path that ends with
  `.git`. For a `skills_root` without a ref, write `<url>#:<skills_root>`.
- A directory, relative to the project or absolute.
- The id of a built-in preset (see [Presets](#presets)).

The default id is `<owner>-<repo>` of a git URL (`mattpocock-skills`) or the directory name of a path.
`--skill-pack` on `agentic install` adds to the saved packs; a pack with the same id replaces the saved one and
keeps its saved `select` and `exclude` in the same way.

TUI: the "Skills" step follows the "Select integrations (MCP / skills)" step, where you choose JEV. See
[TUI](#tui).

## TUI

The "Skills" step is a single select: the project gets one skill pack, or none. The rows:

```text
None
mattpocock/skills · 21 skills · MIT · ★ 333.8k
obra/superpowers · 13 skills · MIT · ★ 327.8k
anthropics/skills · 8 skills · Apache-2.0 · ★ 201.2k (2026-11-27)
Custom source… (git URL or directory)
```

Every row fits an 80-column terminal, also with a dated star count. The footer line shows what the row under
the cursor does, for example `obra/superpowers: brainstorm, plans, TDD, debugging, code review`.

- `None` removes the saved packs (`None (remove the saved pack)` when the project has one).
- A preset row installs that preset ([Presets](#presets)).
- `Custom source…` opens a text input for a git spec `<url>[#ref][:skills_root]`, a directory, or a preset id.
  An empty answer or Esc keeps the saved choice. An invalid spec stops the wizard with the error.
- The cursor starts on the saved choice, so Enter keeps it. For one saved preset that is its row, marked
  `· saved`; the saved entry keeps its lock and overrides. For a saved pack from a URL or a directory (or more
  than one saved pack from `agentic skills add`) a first row `Keep saved: <id> (<source>)` appears. Esc on the
  step also keeps the saved packs.
- Another choice replaces the saved packs. The install removes the files of the old pack in the same way as
  `agentic skills remove` (unedited files only, empty directories pruned).
- After the step, the issue tracker step appears only for the preset `pocock` ([Project setup](#project-setup)).

Each preset row shows the GitHub star count. agentic asks `GET https://api.github.com/repos/<owner>/<repo>`
(`stargazers_count`) when the wizard starts, in the background, one request per preset in parallel, with one
2-second deadline for all of them. The requests are unauthenticated. agentic sends `GITHUB_TOKEN` or `GH_TOKEN`
when one is set and `GH_HOST` is unset or `github.com` (a token for another GitHub installation never goes to
api.github.com). On 401 or 403 with a token, agentic asks once more without it. The counts stay for 24 hours in `~/.cache/agentic/github-stars.json`
(`$XDG_CACHE_HOME/agentic/` when set). In that time the TUI sends no request. Offline, rate-limited, or after
the deadline, the row shows the last cached count or the snapshot that the preset carries, with its date:
`★ 333.8k (2026-11-27)`. The Skills step waits at most 2 seconds more. `AGENTIC_NO_GITHUB_STARS=1` turns the
requests off. A non-interactive `install` and the `skills` subcommands never ask GitHub.

## Settings

`.agentic.json`:

```json
{
  "settings": {
    "skill_packs": [
      {"preset": "pocock", "id": "pocock", "commit": "<40-character commit id>"},
      {
        "id": "mattpocock-skills",
        "git": "https://github.com/mattpocock/skills",
        "ref": "main",
        "skills_root": "skills",
        "select": ["tdd", "grill-me"],
        "exclude": [],
        "commit": "<40-character commit id>"
      },
      {"id": "team", "path": "vendor/skills", "skills_root": ".", "select": [], "exclude": ["draft"]}
    ]
  }
}
```

| Key | Meaning |
|---|---|
| `preset` | A built-in preset (see [Presets](#presets)). The entry then holds only `id`, the overrides that you set (`ref`, `select`, `exclude`), and the lock. The URL, the pinned commit, `skills_root`, and the `select` list come from the preset of the running agentic. |
| `id` | Pack id: letters, digits, `.`, `_`, `-`. Unique in the list. |
| `git` or `path` | The source: a git URL, or a directory relative to the project or absolute. |
| `ref` | Branch, tag, or commit of a git source. Default: the remote `HEAD`. |
| `skills_root` | The directory below the source root that holds the skills. Default `skills`; `.` is the source root. |
| `select` | Skill names to install. Empty: every skill. A name that the pack does not have is an error. |
| `exclude` | Skill names to skip. A name that the pack does not have gives a warning. |
| `commit` | The lock (see [Lock](#lock)). agentic writes it; do not edit it. |

## Layout

A skill is any directory with a `SKILL.md` below `skills_root`, at any depth. agentic flattens nested layouts:
`skills/<category>/<name>/SKILL.md` installs as `<skills dir>/<name>/`, with every file of the skill directory
(scripts, references, templates). agentic does not look for more skills inside a skill directory. It skips
directories whose names start with `.`, `node_modules`, symbolic links, and files that are not UTF-8 text
(with a warning). A skill directory name must use only letters, digits, `.`, `_`, and `-` (not `.` or `..`);
agentic skips another name with a warning.

agentic never follows a symbolic link of the source: a symlinked `SKILL.md`, skill directory, or license is
skipped, and a symlinked `skills_root` (or a component of it) is an error. Files outside the source never reach
the project.

| Source | Written to | Hosts |
|---|---|---|
| `<skills_root>/**/<name>/**` | `.claude/skills/<name>/`, `.agents/skills/<name>/`, `.opencode/skills/<name>/`, and the skills directory of every other selected host | every selected host |
| same | `.agent/skills/<name>/` | always |
| `LICENSE` (or `LICENSE.md`, `LICENSE.txt`, `LICENCE`, `LICENCE.md`, `COPYING`) at the source root | `.agent/skill-packs/<id>/LICENSE` | always |
| a license file inside a skill directory (for example `LICENSE.txt` of each anthropics/skills skill) | with the skill, like every skill file | every selected host |

The license copy is outside every host skills directory, so no host reads it as a skill. The upstream text is
unchanged, except a frontmatter marker in Markdown: `SKILL.md` and other `*.md` files get an `agentic:` block
inside their frontmatter (also with CRLF line endings). Other files (scripts, JSON, SVG, CSV, the license) are
copied byte for byte; the manifest `content_hash` alone tracks them. A file with an execute bit upstream (a
script that a skill runs by its path) gets exactly the upstream execute bits, within the umask (Unix). Install,
`agentic skills`, and `agentic upgrade` give the same modes: the staging transaction carries the execute bits,
and a new file gets the normal mode of the umask (for example `0644`). When upstream drops the bit, the next
update drops it too. Git checkouts of packs use
`core.autocrlf=false`, so upstream line endings stay.

Manifest entries have `marker: skill-pack` and `source: skill-pack:<id>/<name>/<path>` (license:
`skill-pack:<id>/LICENSE`). The managed-file rules apply: install skips a file that you edited, and upgrade
merges your edits or keeps a backup ([upgrade behavior](agentic-upgrade/README.md)). Before the first install,
an existing file without the agentic marker belongs to you; install keeps it and prints a warning. The same
holds for `agentic skills` and `agentic upgrade`: every host skills directory (for example `.agents/skills` of
Codex) is in the project inventory, so a skill of your own with the name of a pack skill stays unchanged and is
reported as a preserved user file.

## Hosts

Every host gets the same skill set and the same upstream skill text. A skill is user-invoked when the top-level
frontmatter of its `SKILL.md` has `disable-model-invocation: true` (quoted or with a trailing `# comment` as
well; the Claude Code key; for example `grill-me`,
`to-spec`, `handoff` of mattpocock/skills). The model does not start a user-invoked skill by itself; the user
starts it. agentic gives each host the entry point that the host supports:

| Host | Discovery | Model-invoked skill | User-invoked skill | What agentic adds |
|---|---|---|---|---|
| Claude Code | `.claude/skills/<name>/SKILL.md` | the model loads it; the user can type `/<name>` | `/<name>`; Claude reads `disable-model-invocation` | nothing |
| OpenCode | `.opencode/skills/<name>/SKILL.md` (also `.claude/skills` and `.agents/skills`) | the model loads it with the `skill` tool; the user can write `@<name>` | `/<name>`; OpenCode reads `disable-model-invocation` (since anomalyco/opencode#52747, October 2026) and hides the skill from the model | `.opencode/commands/<name>.md`: "Load the skill `<name>` with the skill tool and follow its instructions", with `$ARGUMENTS` and the skill `description` |
| Codex | `.agents/skills/<name>/SKILL.md`; ignores unknown frontmatter keys | the model loads it by its `description`; the user can type `$<name>` | `$<name>` or `/skills`; Codex does not read `disable-model-invocation` | `.agents/skills/<name>/agents/openai.yaml` with `policy: allow_implicit_invocation: false` |
| other hosts, `.agent/skills` | the host skills directory | as the host does | as the host does | nothing |

Rules:

- agentic does not change the upstream files. Only the agentic marker goes into the frontmatter (see
  [Layout](#layout)).
- A skill that ships its own `agents/openai.yaml` keeps that file. When the file does not set
  `allow_implicit_invocation`, install prints a warning: Codex can start the skill without `$<name>`.
- The OpenCode command is Markdown and gets the agentic marker. `agents/openai.yaml` is written as it is,
  without a marker; the manifest hash tracks it (only Markdown pack files get the marker).
- The new files have `marker: skill-pack` and the sources `skill-pack:<id>/<name>/@opencode/command.md` and
  `skill-pack:<id>/<name>/@codex/agents/openai.yaml`. `agentic skills list` counts them with their skill. Remove
  and update remove them with the skill.
- An OpenCode command with the same name that another agentic step installs (for example
  `.opencode/commands/profile.md`) stops the install with an error. Add the skill to the `exclude` list.
- An older OpenCode ignores `disable-model-invocation`: the model there can also start the skill. The
  `/<name>` command works in both cases.

Sources: [Codex skills](https://learn.chatgpt.com/docs/build-skills) (`agents/openai.yaml`, `policy`),
[OpenCode skills](https://opencode.ai/docs/skills/) and [commands](https://opencode.ai/docs/commands/),
[Claude Code skills](https://docs.claude.com/en/docs/claude-code/skills).

## Name conflicts

A conflict stops the install with an error; agentic never overwrites one skill with another:

- Two skills with the same name in one pack (for example `skills/a/tdd/` and `skills/b/tdd/`).
- A pack skill with the name of an agentic skill of the selected specializations (for example `api-design` of
  `software.backend`), of `agentic-profile`, or of a company skill ([company rules](company-rules.md)).
- The same skill name in two packs.

The error names both skills. Add one of them to the `exclude` list of its pack.

## Lock

- The first install of a git pack fetches `ref` and writes the commit id to `commit`.
- `agentic install` and `agentic upgrade` check out the locked commit, not the newest commit of `ref`. Upstream
  changes do not reach the project by surprise.
- `agentic skills update [<id>]` fetches `ref` again, writes the new commit, and installs it.
- `agentic skills add` with a new source or `skills_root` resolves the ref again.
- A path source has no lock: install reads the directory as it is.

## Remove and update

agentic removes only the files that the manifest records for the pack (`marker: skill-pack`):

- `agentic skills remove`, `agentic skills update`, and `agentic upgrade` remove the files that the pack no longer
  installs, as obsolete artifacts. `agentic skills` also removes the empty skill directories.
- A repeated `agentic install` removes them too, with their empty directories.
- A file that you edited stays, with a warning. Your own skills in the same directories are never touched.

## Offline and errors

- Git: the cache is `~/.cache/agentic/skill-packs/<sha256(url)>` (`$XDG_CACHE_HOME` when set). agentic fetches
  with `git fetch --depth 1` and never asks for credentials, as for company rules.
- A locked commit comes from the cache when it is there; otherwise agentic fetches that commit.
- A failed fetch never changes the lock. `agentic install` and `agentic upgrade` use the locked commit from the
  cache; when the cache does not have it, they print a warning and keep the files that the pack installed
  before. Nothing is removed.
- `agentic skills update` with a failed fetch stops with an error (`the lock stays at <commit>`) and changes
  nothing.
- A pack without installed files and without a lock (`agentic skills add`, `--skill-pack` on a first install)
  must be readable: a failed fetch or a missing directory stops with an error, and the pack is not saved.
- `ref` and `commit` are checked before git runs: a `ref` must not start with `-` or hold whitespace or control
  characters, and `commit` must be a full 40- or 64-digit hex commit id. agentic also passes `--` before the
  remote and the ref, so a value from `.agentic.json` is never read as a git option.
- A missing `skills_root` directory, an unknown `select` name, an invalid id, or a duplicate id is an error.

## Shared source code

Company rules and skill packs share `src/source.rs`: the `Source` type (path or git), the `<url>[#ref][:subdir]`
parser, URL redaction, the git cache and fetch, and the file walk. `src/skill_packs.rs` holds the pack logic.

## Extension points

- Host adaptation: `skill_packs::adapt_for_host(host, skill, rel, content)` runs for every file and host before
  the write and returns the upstream text unchanged. `skill_packs::host_entry_files(host, dir, skill)` returns
  the files that a host needs in addition (see [Hosts](#hosts)).
- Presets: `skill_packs::PRESETS` lists the built-in packs (`id`, `repo`, `summary`, `license`, `url`, `git_ref`,
  `skills_root`, `select`, and the star snapshot `stars`/`stars_date`). An entry makes `agentic skills add <id>`
  and `--skill-pack <id>` work and adds a row to the TUI "Skills" step, in list order. The project setup of
  `pocock` is in `src/pocock_setup.rs`; the star counts are in `src/github_stars.rs`.

## Presets

| Id | Source | Author | License | Pinned commit | Skills |
|---|---|---|---|---|---|
| `pocock` | [mattpocock/skills](https://github.com/mattpocock/skills) | Matt Pocock | MIT (root `LICENSE`) | `6f7f7831a625f040a8e06a0e7954826b87ce775a` | 21 ([Preset pocock](#preset-pocock)) |
| `superpowers` | [obra/superpowers](https://github.com/obra/superpowers) | Jesse Vincent (obra) | MIT (root `LICENSE`) | `22f0b463e7a5e579904dd6211a520321035526f7` | 13 ([Preset superpowers](#preset-superpowers)) |
| `anthropic` | [anthropics/skills](https://github.com/anthropics/skills) | Anthropic | Apache-2.0 (`LICENSE.txt` in each skill; no root license) | `e4bb5d960d87126ff3b3a8af1a104b7db67560ba` | 8 ([Preset anthropic](#preset-anthropic)) |

`agentic skills add <id>` and `agentic install --skill-pack <id>` use a preset, for example
`agentic skills add superpowers` or `agentic install --skill-pack anthropic`. `--select` and `--exclude`
replace the list of the preset; without them the preset list stays. `<id>#<ref>` (for example `pocock#<ref>`) sets your own ref.
`--skills-root` is not allowed for a preset.

`.agentic.json` keeps a preset as `{"preset": "<id>", "id": ..., "commit": ...}` plus only the overrides that
you set. So a newer agentic brings the newer pin and `select` list of the preset to the project. When the pin of
the preset differs from the lock and you did not set `ref`, install and upgrade move the lock to the new pin
and log it. If the new pin cannot be fetched, the lock and the installed files stay, with a warning. A preset id
that the running agentic does not know is an error.

### Preset pocock

Attribution: the skills and the setup templates come from [mattpocock/skills](https://github.com/mattpocock/skills),
MIT license, author Matt Pocock. agentic copies the license to `.agent/skill-packs/pocock/LICENSE`.

The preset pins a commit of `main` in `ref`, so every install gets the same text. `skills update` does not
move a pinned commit; a new agentic release changes the pin, and the next install or upgrade moves the lock.

Selected skills: `grilling`, `grill-me`, `grill-with-docs`, `to-spec`, `to-tickets`, `domain-modeling`, `tdd`,
`implement`, `implement-spec`, `code-review`, `diagnosing-bugs`, `codebase-design`,
`improve-codebase-architecture`, `prototype`, `research`, `handoff`, `wayfinder`, `retro`, `wizard`, `pr`,
`writing-for-agents`. Not selected: `setup-matt-pocock-skills` (agentic replaces it, see below), `triage`,
`ask-matt`, `teach`, `wait-what`, `to-questionnaire`, and the `in-progress/` and `misc/` skills.

#### Project setup

The upstream skills `to-spec`, `to-tickets`, `implement-spec`, `code-review`, and `wayfinder` expect an issue
tracker description, and `grill-with-docs` and `domain-modeling` expect the domain doc layout. Upstream, the
prompt-driven skill `setup-matt-pocock-skills` writes these files. agentic writes them at install time instead:

```bash
agentic install --project-dir . --skill-pack pocock --issue-tracker gitlab
agentic skills add pocock --issue-tracker github
```

`--issue-tracker` is `local` (default), `github`, or `gitlab`. The TUI asks for it after the "Skills" step when
the pack is `pocock`; the cursor starts on the saved choice (`local` without one), so Enter keeps it.
`.agentic.json` keeps the choice in `settings.issue_tracker`; a later install or upgrade replays it.

| File | Content |
|---|---|
| `docs/agents/issue-tracker.md` | `local`: markdown files under `.scratch/<feature>/`. `github`: the `gh` CLI. `gitlab`: the `glab` CLI (issues, notes, labels, merge requests). Each variant also has the wayfinder operations. |
| `docs/agents/triage-labels.md` | The five default triage labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). `to-spec` and `to-tickets` apply `ready-for-agent`. |
| `docs/agents/domain.md` | Single-context layout: `GLOSSARY.md` and `docs/adr/` at the root, and the rules for reading them. The skills create `GLOSSARY.md` and the ADRs when needed. |
| `AGENTS.md` (generated section `## Agent skills`) | One line each for the tracker, the labels, and the domain docs, with links to the three files. About 150 tokens of always-on context. The section sits right after the header, between `<!-- agentic:agent-skills:begin -->` and `<!-- agentic:agent-skills:end -->`, so your edits at the end of AGENTS.md merge without a conflict on upgrade. When AGENTS.md already has its own `## Agent skills` heading outside this block, agentic keeps yours, does not add a second one, and prints a warning. In `--agents-md keep` mode the section is in `.agent/AGENTS.md`. |

agentic also installs its own small skill `setup-matt-pocock-skills` on every host, next to the pack skills
(`disable-model-invocation: true`, agentic marker, manifest source `skill-pack:pocock/setup-matt-pocock-skills/SKILL.md`).
The upstream skills still say "run `/setup-matt-pocock-skills`"; the text stays unchanged. This skill tells the
agent to read `docs/agents/*.md` and to run `agentic skills add pocock --issue-tracker ...` to change the setup.
It is not the upstream skill, and `skills remove pocock` removes it. Like a user-invoked pack skill, it gets the
host entry points from [Hosts](#hosts): `.opencode/commands/setup-matt-pocock-skills.md` and
`.agents/skills/setup-matt-pocock-skills/agents/openai.yaml`. The upstream `setup-matt-pocock-skills` is
never installed, even when `--select` names it. Another pack skill or company skill with that name is an error:
exclude it from the other pack, or rename the company skill.

The setup (the `docs/agents/` files, the AGENTS.md section, and this skill) follows the preset, not the id:
`skills add pocock --id mp` gets the setup with sources `skill-pack:mp/...`, and a pack from a URL with
`--id pocock` gets none.

The three `docs/agents/` files are skill pack files in the manifest (`marker: skill-pack`, source
`skill-pack:pocock/setup.<name>`). The managed-file rules apply: install keeps a file that you edited, and
`agentic skills remove pocock` removes the files that you did not edit. A file of your own that is already in
`docs/agents/` (for example from the upstream `/setup-matt-pocock-skills`) stays unchanged: install, `agentic
skills`, and `agentic upgrade` report it as a preserved user file and write the other files. agentic does not run `gh label create`
or `glab label create` and does not create the remote repository; the skills use the labels that the tracker
has. The upstream multi-context layout (`GLOSSARY-MAP.md`) and other trackers are not set up: edit
`docs/agents/*.md` by hand.

### Preset superpowers

Attribution: the skills come from [obra/superpowers](https://github.com/obra/superpowers), MIT license, author
Jesse Vincent. agentic copies the license to `.agent/skill-packs/superpowers/LICENSE`.

Upstream ships the skills as a Claude Code plugin with a `SessionStart` hook. The hook injects the skill
`using-superpowers` into every session. agentic installs no hooks, so the preset selects only the skills that
work as plain skills on every host: `brainstorming`, `writing-plans`, `executing-plans`,
`subagent-driven-development`, `dispatching-parallel-agents`, `test-driven-development`, `systematic-debugging`,
`verification-before-completion`, `requesting-code-review`, `receiving-code-review`, `using-git-worktrees`,
`finishing-a-development-branch`, `writing-skills`.

Not selected:

- `using-superpowers`: the plugin hook loads it at session start. As a plain skill it orders a skill check
  before every answer, also a clarifying question, which conflicts with the "Scale the process to the task"
  rule of the generated AGENTS.md.
- `diagnosing-superpowers`: it reads the transcripts of superpowers plugin sessions and drafts bug reports for
  the superpowers maintainers. It is not a project skill.

The skill texts name other skills as `superpowers:<name>` (the plugin namespace). Installed by agentic, the
skill is `<name>`; the agent finds it by that name. `executing-plans` and `subagent-driven-development` run
their bundled scripts (`scripts/task-start`, `scripts/sdd-workspace`) by path; agentic keeps the execute bits
([Layout](#layout)). Some scripts and `brainstorming` (the visual companion) need `bash` or `node`.

Known limitation: `executing-plans` and `writing-skills` link to `../using-superpowers/references/` (the
harness tool notes of the excluded skill). Those links point to nothing in the project; the skills work without
them.

### Preset anthropic

Attribution: the skills come from [anthropics/skills](https://github.com/anthropics/skills), author Anthropic.
Each selected skill has its own Apache-2.0 `LICENSE.txt`, which agentic installs with the skill. The repository
has no root license, so `.agent/skill-packs/anthropic/` stays empty. The upstream `THIRD_PARTY_NOTICES.md`
covers fonts, FFmpeg, imageio, and Pillow, which the selected skills do not ship.

Selected skills (developer tools): `skill-creator`, `mcp-builder`, `webapp-testing`, `frontend-design`,
`docx`, `pdf`, `pptx`, `xlsx`.

Not selected:

- `web-artifacts-builder`: its init script needs the binary `scripts/shadcn-components.tar.gz`; agentic
  installs only UTF-8 text files ([Layout](#layout)).
- `doc-coauthoring`: it has no license file at the pinned commit.
- `claude-api`: Claude Code has a built-in skill with the same name; a project skill would shadow or duplicate
  it.
- Brand, organization, or art skills: `brand-guidelines`, `internal-comms`, `slack-gif-creator`,
  `academy-guide`, `discernment-nudge`, `theme-factory`, `algorithmic-art`, `canvas-design`.
- `template/` and `spec/` are outside `skills_root` and are never skills.

Several skills (`docx`, `pdf`, `pptx`, `xlsx`, `webapp-testing`) run Python scripts
and need the Python packages that their `SKILL.md` names.

## Check

- `cargo test --bin agentic skill_packs`: spec parsing and ids, settings and replay, flattening for every host,
  host parity (the same skills on Claude Code, Codex, and OpenCode, a user entry point for each user-invoked
  skill, nothing left after remove), the pack's own `agents/openai.yaml`, an OpenCode command clash,
  the license copy, `select` and `exclude`, every name conflict, removal on reinstall, the offline fallback, and
  the commit lock with a local git repository.
- `cargo test --bin agentic source`: the shared source code and the checkout of a locked commit.
- `cargo test --test cli skill_pack`: `install --skill-pack`, `skills add|list|update|remove` with a local bare
  repository, and the conflict error.
- `cargo test --bin agentic pocock`: the preset, its `select` list against a fixture, the setup files for each
  tracker, a repeated install, user edits, and removal.
- `cargo test --bin agentic preset`: the order and fields of every preset, the `superpowers` and `anthropic`
  `select` lists against fixtures (excluded skills, per-skill licenses, no root license, execute bits), the
  execute bits and file modes after `skills add` and upgrade (the staging transaction), and all three presets
  side by side without a name clash.
- `cargo test --bin agentic tui::`: the "Skills" step right after the JEV step, its rows (80 columns), the
  hint line, the preselected
  saved pack, none/preset/custom/keep/replace, and removal on the next install.
- `cargo test --bin agentic github_stars`: the `k`/`M` format, the snapshot with its date, and the cache
  (write, 24-hour expiry, broken file), and the token rules. The tests never use the network.
