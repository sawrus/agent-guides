---
covers:
  - src/company.rs
  - src/copydir.rs
  - src/manifest.rs
  - src/agentsmd.rs
  - src/project_update.rs
  - src/tui.rs
---

# Company rules

Status: implemented. Company rules are rule files that an organisation or a project keeps outside the
agent-guides pack. `agentic install` copies them into the project next to the pack rules. A company rule wins
over a pack rule on the same topic ([artifact standard](artifact-standard.md), P2 and ART-K1..K3).

## Purpose

- Keep internal standards (internal systems, hosts, team conventions) out of the public pack (ART-K3).
- Install them with the same command, for every host, and keep them current on `agentic upgrade`.
- Drop the pack rules that a company rule replaces, so the agent does not read two rules on one topic.

The feature is opt-in. Without `settings.company_rules` in `.agentic.json`, install and upgrade work as before.

## Configuration

`.agentic.json`:

```json
{
  "settings": {
    "company_rules": {
      "sources": [
        {"path": ".agent/company"},
        {"git": "git@gitlab.example.com:group/standards.git", "ref": "main", "subdir": "rules"}
      ],
      "exclude": ["software/backend/testing"]
    }
  }
}
```

| Key | Meaning |
|---|---|
| `sources[].path` | A directory with rule files, relative to the project or absolute. |
| `sources[].git` | A git URL. `ref` (branch, tag, or commit; default: the remote `HEAD`) and `subdir` (default: the repository root) are optional. |
| `exclude` | Pack rule ids `<area>/<spec>/<rule>` that the install skips. |

CLI (`agentic install`; each flag can repeat):

```bash
agentic install --project-dir /path/to/project --agent-os claude,codex \
  --areas software --specializations software.backend \
  --company-rules-git 'git@gitlab.example.com:group/standards.git#main:rules' \
  --company-rules-path .agent/company \
  --company-rules-exclude software/backend/testing
```

- `--company-rules-git <url>[#ref][:subdir]`. For a subdir without a ref, write `<url>#:<subdir>`.
- `--company-rules-path <dir>`.
- `--company-rules-exclude <id>` (also a comma-separated list).

On a repeated install, CLI sources replace the saved sources, and CLI excludes are added to the saved list.
`agentic upgrade` replays `settings.company_rules` from the manifest. To turn the feature off, remove
`settings.company_rules` from `.agentic.json` and run `agentic upgrade`.

TUI: after the specializations, the optional "Company rules" step asks for a directory and a git repository.
Empty answers keep the feature off. The fields start with the values saved in the project manifest; the saved
`exclude` list stays.

## Source layout

A source holds Markdown rule files, usually one directory per area: `<source>/<area>/<name>.md`, for example
`rules/software/api.md` with `subdir: rules`. Install reads every `*.md` file below the source root. It skips
`README.md` files, directories whose names start with `.`, and the top-level `skills/` and `workflows/`
directories (see [Company skills and workflows](#company-skills-and-workflows)). A rule file follows the rule requirements of the
[artifact standard](artifact-standard.md). Frontmatter keys that install reads:

| Key | Effect |
|---|---|
| `paths:` | Scopes the rule. Claude Code loads a rule without `paths:` in every session; install prints a warning for it. |
| `trigger: manual` | The rule stays in `.agent/company/` only; Claude Code gets no copy. |
| `replaces: [<area>/<spec>/<rule>]` | The named pack rules are excluded, as if they were in `exclude`. |

When two sources have the same relative path, the first source wins and install prints a warning.

## Company skills and workflows

A source can also hold skills and workflows next to its rules. Install treats them as pack skills and
workflows of the selected hosts, never as rules:

```text
<source>/
├── software/api.md                    # rule
├── skills/release-notes/SKILL.md      # skill: every file below skills/<name>/ (scripts, templates)
└── workflows/hotfix.md                # workflow: workflows/<id>.md (README.md is skipped)
```

| Source file | Written to | Hosts |
|---|---|---|
| `skills/<name>/**` | the skills directory of each host (`.claude/skills`, `.agents/skills`, `.opencode/skills`, ...) and `.agent/skills/<name>/` | every host |
| `workflows/<id>.md` | `.agent/workflows/<id>.md` and the workflows directory of each host (`.opencode/commands`, ...) | every host |
| `workflows/<id>.md` | `.claude/commands/<id>.md`: a thin wrapper that runs `@.agent/workflows/<id>.md`, like pack workflows | `claude` |

- A skill or workflow with the name of a pack skill or workflow of the selected specializations replaces it on
  every host. When the source drops it, `agentic upgrade` restores the pack version.
- Skills and workflows follow the [artifact standard](artifact-standard.md) (skills at most 250 lines,
  workflows at most 120 lines and 6 steps).
- The manifest source is `company:<source-id>/skills/<name>/<path>` or `company:<source-id>/workflows/<id>.md`.
  Upgrade, the offline fallback, and the managed-file rules work as for rules.
- When two sources have the same `skills/<name>/<path>` or `workflows/<id>.md`, the first source wins.

## What install writes

| File | Hosts | Manifest |
|---|---|---|
| `.agent/company/<area>/<name>.md` | every host | `marker: company`, `source: company:<source-id>/<relpath>` |
| `.claude/rules/company-<area>-<name>.md` | `claude` | same |
| `AGENTS.md`: one line `Company rules in .agent/company/ override agent-guides rules on conflict.` | every host | — |

- The source id is the path as configured, or the git URL with `#ref` and `:subdir`. Install hides the user part
  of an `https://user:token@host` URL; do not put tokens in URLs anyway, because `settings` keeps the URL.
- A path source that is `.agent/company` itself is used in place: install does not copy or mark its files, and
  Claude Code still gets its copies. Files in that directory that carry the agentic marker (copies from other
  sources) are not read again.
- Files that you create in `.agent/company/` and that no source provides are never changed or removed. A file of
  yours with the same path as a source file is kept too: install prints a warning and skips it. An edited copy
  follows the managed-file rules: install skips it, upgrade merges or keeps a backup
  ([upgrade behavior](agentic-upgrade/README.md)).
- Excluded pack rules are not copied for any host. A repeated `agentic install` removes the excluded pack rules
  that an earlier install wrote, unless you edited them. `agentic upgrade` removes them as obsolete artifacts, as
  well as company files that a source no longer has.

## Git sources

- Install fetches into `~/.cache/agentic/company/<sha256(url)>` (`$XDG_CACHE_HOME` when set) with the `git` CLI:
  `git fetch --depth 1 origin <ref>`, then a checkout of `FETCH_HEAD`. The project gets copies; the cache is only
  read.
- Git never asks for credentials: install sets `GIT_TERMINAL_PROMPT=0`, `GCM_INTERACTIVE=never`, and, when
  `GIT_SSH_COMMAND` is not set, `ssh -o BatchMode=yes`. Use an SSH key or a credential helper.
- When the fetch fails (offline, no access), install uses the cached copy and prints a warning. Without a cached
  copy, install prints a warning and keeps the files that the source installed before, so an offline upgrade
  removes nothing.

## Duplicate report

After `agentic install` and `agentic upgrade` with company sources, agentic runs the embedded
`scripts/check_artifacts.py --project <dir> --json` with `python3` (3.11+) and prints:

```text
=== Company rules vs pack rules ===
- .agent/company/software/testing.md covers pack rule .agent/rules/testing.md: add `replaces: [software/backend/testing]` to it, or install with --company-rules-exclude software/backend/testing
```

The report lists ART-K1 (topic overlap, `replaces:` errors) and ART-K2 (restated statements) findings. It never
fails the install. Without `python3`, agentic prints `Company rules duplicate check skipped: ...`. The full check
of company rules (ART-C*, ART-R*) is `python3 scripts/check_artifacts.py --project <dir>` in an agent-guides
checkout.

## Check

- `cargo test --test cli company_rules`: path source, git source with ref and subdir from a local bare
  repository, `exclude` and `replaces:`, upgrade replay of a new commit, offline fallback, the `AGENTS.md` line,
  preserved user files, and the duplicate report.
- `cargo test --bin agentic company`: parsing of git specs, settings, frontmatter, and URL redaction.
