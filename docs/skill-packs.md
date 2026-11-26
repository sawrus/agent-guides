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
---

# Skill packs

Status: implemented. A skill pack is a set of ready-made skills in an external git repository or a local
directory, for example [mattpocock/skills](https://github.com/mattpocock/skills) (MIT). agentic installs the
skills of a pack into the skills directory of every selected host. agentic does not rewrite the skills.

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
agentic skills add https://github.com/mattpocock/skills --id pocock --select tdd,grill-me
agentic skills add ./vendor/skills --skills-root . --exclude draft-skill
agentic skills list
agentic skills update            # every pack
agentic skills update pocock     # one pack
agentic skills remove pocock
```

| Command | Effect |
|---|---|
| `skills add <spec> [--id <id>] [--select a,b] [--exclude x,y] [--skills-root <dir>]` | Adds the pack, or replaces the pack with the same id. A pack with the same source and `skills_root` keeps its locked commit. |
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
`--skill-pack` on `agentic install` adds to the saved packs; a pack with the same id replaces the saved one.

TUI: after the "Company rules" step, the optional "Skill pack" step asks for one git spec or directory. An
empty answer keeps the saved packs.

## Settings

`.agentic.json`:

```json
{
  "settings": {
    "skill_packs": [
      {
        "id": "pocock",
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

The license copy is outside every host skills directory, so no host reads it as a skill. The upstream text is
unchanged, except a frontmatter marker in Markdown: `SKILL.md` and other `*.md` files get an `agentic:` block
inside their frontmatter (also with CRLF line endings). Other files (scripts, JSON, SVG, CSV, the license) are
copied byte for byte; the manifest `content_hash` alone tracks them. Git checkouts of packs use
`core.autocrlf=false`, so upstream line endings stay.

Manifest entries have `marker: skill-pack` and `source: skill-pack:<id>/<name>/<path>` (license:
`skill-pack:<id>/LICENSE`). The managed-file rules apply: install skips a file that you edited, and upgrade
merges your edits or keeps a backup ([upgrade behavior](agentic-upgrade/README.md)). Before the first install,
an existing file without the agentic marker belongs to you; install keeps it and prints a warning. The same
holds for `agentic skills` and `agentic upgrade`: every host skills directory (for example `.agents/skills` of
Codex) is in the project inventory, so a skill of your own with the name of a pack skill stays unchanged and is
reported as a preserved user file.

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
  the write. Today it returns the upstream text unchanged. Host-specific frontmatter (for example
  `disable-model-invocation`) plugs in there.
- Presets: `skill_packs::PRESETS` lists the built-in packs (`id`, `url`, `git_ref`, `skills_root`). An entry
  makes `agentic skills add <id>` and `--skill-pack <id>` work. The list is empty today.

## Presets

No built-in preset exists yet. Use the URL, for example
`agentic skills add https://github.com/mattpocock/skills --id pocock`.

## Check

- `cargo test --bin agentic skill_packs`: spec parsing and ids, settings and replay, flattening for every host,
  the license copy, `select` and `exclude`, every name conflict, removal on reinstall, the offline fallback, and
  the commit lock with a local git repository.
- `cargo test --bin agentic source`: the shared source code and the checkout of a locked commit.
- `cargo test --test cli skill_pack`: `install --skill-pack`, `skills add|list|update|remove` with a local bare
  repository, and the conflict error.
