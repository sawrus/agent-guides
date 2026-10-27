# repo-scan v3 design: repository slices, LLM skip classes, any Git host

Status: design, not implemented. Target release: `v3.0.0` (feature plus a changed file layout, see
[release-policy.md](release-policy.md)). User page: [repo-scan.md](repo-scan.md). Tool reference:
[tools/repo-scan/README.md](../tools/repo-scan/README.md).

## Goals

- G1. One target repository: scan it as the focus, resolve its links across all context roots (cross scan), and
  write the full result of stage 1 and stage 2 into `<repo>/.agentic/repo-scan/`.
- G2. All roots at once (for example two groups): the same flag writes one slice into each repository.
- G3. Do not call the LLM for repositories that stage 1 classifies as not worth it: `archived`, `junk`, `docs`,
  and two new classes, `trial` (test, demo, learning) and `scripts` (a script dump, not a service).
- G4. Work with any Git host laid out as `~/work/<host>/<path>`: GitLab and GitHub (github.com and GitHub
  Enterprise), not only GitLab.

Acceptance criteria:

1. `repo-scan.sh run <repo> --write-repo-artifacts` creates the six files of [Repository slice](#1-repository-slice)
   in `<repo>/.agentic/repo-scan/`; `git -C <repo> status --porcelain` stays empty.
2. `repo-scan.sh run --write-repo-artifacts` with `REPO_SCAN_ROOTS` set to two roots writes a slice into every
   `active`, `stale` and `scripts` repository and into no other repository.
3. Stage 2 never calls the provider for a repository in `llm_skip_classes`, also in focus mode and with `--repo`.
   `llm-assessment.json` lists it with `"status": "skipped"` and the reason. `--llm-all-classes` restores the call.
4. A tree `~/work/github.com/<owner>/<repo>` gets `https://github.com/<owner>/<repo>` ids, `forge: github`, and
   `ci` edges from GitHub Actions `uses:` references to repositories in the scanned roots.
5. `make test` and `make lint` pass.

Non-goals:

- Group labels (such as a team name per root). The root URL is enough.
- A new wrapper command. The existing `run` and `scan` take the flag.
- Writing `.agent/gate.json`. Only `gate-verify` writes it, as today.
- Commits or pushes in analyzed repositories.
- Network access in stage 1 (no GitLab or GitHub API calls).

## Current state (v2.2.0)

| Topic | Where | Behavior |
|---|---|---|
| Identity | `reposcan/discover.py`: `identity`, `expected_url` | Host comes from the path `~/work/<host>/<path>` or from `--root-url`. Already host-neutral, but docs, help and comments say "GitLab URL". |
| Root URLs | `cli.py`: `cmd_scan`, `--root-url`; wrapper `REPO_SCAN_ROOT_URLS` | Any `http(s)` URL is accepted. Help text names GitLab only. |
| Focus mode | `cli.py`: `cmd_scan`, `context_roots`, `focus_view` | Context roots are scanned; output keeps the focus repositories, their edges and direct neighbours. Default context root is `<host>/<group>` above the focus. |
| Repository files | `cli.py`: `write_repo_artifacts` | `--write-repo-artifacts` writes `.agentic/repo-scan.json` and `.agentic/dependencies.json`. It runs inside `cmd_scan`, so it never sees stage 2. |
| Stage 2 selection | `cli.py`: `cmd_llm`, `cmd_run` | `--repo` or focus repositories are assessed whatever their class. Without them, `--classes active`. |
| Classes | `discover.py`: `classify`; `applicability.json` → `activity` | `archived`, `junk`, `docs`, `active`, `stale`. No class for trial repositories; a script dump with CI or 100+ lines is `active` or `stale`. |
| CI links | `relations.py`: `ci_and_deploy` | Only `.gitlab-ci.yml` `include: project:`. GitHub workflows are parsed (`manifests.py`: `parse_github_workflow`: jobs and `run:` lines) but `uses:` is not read. |
| Libraries | `relations.py`: `libraries` | `go.mod` modules such as `github.com/org/lib` already resolve by module name. Git URL dependencies (`git+https://...`, `github:org/repo`) are not resolved. |
| Deploy | `relations.py`: `ci_and_deploy` | ArgoCD `repoURL` resolves by URL key, host-neutral. |
| LLM excerpts | `llm.py`: `build_prompt`, `excerpt` | `README*`, `Makefile`, `.gitlab-ci.yml`. No GitHub workflow. |
| Gate candidates | `gates.py`: `propose_for` | Makefile, `.gitlab-ci.yml`, and `.github/workflows/*`. Already host-neutral. |

## Design

### 1. Repository slice

`--write-repo-artifacts` writes `<repo>/.agentic/repo-scan/`:

| File | Content |
|---|---|
| `repositories.json` | Same meta as `OUT/repositories.json`; records of this repository (`"focus": true`) and its direct neighbours. No `local_path`, no `root_paths`. |
| `relationships.json` | `focus_view(rel, {id}, trusted_min)` of the full graph: edges in and out, unresolved links, stats. |
| `guide-applicability.json` | `guide_ids` plus `repositories` with this repository only. |
| `graph.mmd` | `mermaid()` over the slice records and edges. |
| `gate-proposal.json` | `gates.propose_for(local_path)` with `"note": "candidates only; nothing was executed"`. |
| `llm-assessment.json` | Only after `run`: `provider`, `model`, `prompt_version`, and the entry of this repository (`ok`, `error` or `skipped`). |

Rules:

- The slice is computed per repository from the full graph (before the focus filter), so focus mode (G1) and a
  scan of all roots (G2) share one code path. Move the neighbour selection and the meta block of `cmd_scan` into a
  small helper and use it for `OUT` and for each slice.
- Scan of all roots: write slices only for `slice_classes` in `applicability.json` (default `active`, `stale`,
  `scripts`). Focus mode writes the focus repositories whatever their class.
- `cmd_scan` keeps the list of written slices (`id` → `local_path`). `cmd_run` runs stage 2, then writes
  `llm-assessment.json` into each slice. `llm` as a separate command does not touch repositories.
- `.agentic/` stays in `.git/info/exclude` (`git_exclude`). Nothing is committed.
- Breaking: the old files `.agentic/repo-scan.json` and `.agentic/dependencies.json` are not written any more and
  are removed when a new slice is written. `UPGRADE.md` maps old fields to new files: `repo-scan.json` →
  `repositories.json` (focus record) + `guide-applicability.json`; `dependencies.json` → `relationships.json`
  (`outgoing` = edges with `from` = id, `incoming` = edges with `to` = id).
- Never write secrets: the slice uses the same sanitized records as `OUT`.

### 2. New activity classes

Order of checks in `classify`: `archived` → `junk` (path segments, names) → **`trial`** → `docs` (names) →
`junk` (no HEAD) → `docs` (doc ratio) → **`scripts`** → `junk` (no CI and few lines) → `active` / `stale`.
Each decision returns `reasons`.

`trial` (test, demo, learning repositories), by name only:

- `activity.trial_names`: exact repository names, default `test`, `tests`, `demo`, `poc`, `example`, `examples`,
  `sample`, `samples`. (`playground` and `sandbox` segments are already `junk`.)
- `activity.trial_patterns`: shell globs over the repository name and path segments, default `test-*`, `*-test`,
  `test_*`, `*_test`, `demo-*`, `*-demo`, `poc-*`, `*-poc`, `hello-*`, `*-example`, `example-*`, `learn-*`,
  `tutorial*`.
- Not trial: `autotests`, `*-autotests`, `e2e*`, `qa-*`, `*-tests` of a service (`activity.trial_exclude`, default
  `autotests`, `*-autotests`, `e2e*`, `*-e2e`, `qa-*`). These are real repositories and keep their class.
- Reason example: `name matches trial pattern: demo-*`.

`scripts` (a script dump, not a service), from data stage 1 already has:

- No service markers: no `dockerfile`, `docker-compose`, `helm`, `argocd`, `proto`, no published package
  (`publishers` in `relations.py`), no application manifest with a name (`pyproject` / `package-json` / `go-mod`).
- Script share: lines of `Shell` (and `PowerShell`, `Batch`) plus Python files that are not inside a package
  (no `__init__.py` in their directory) are at least `activity.scripts_min_ratio` (default `0.6`) of code lines.
- At least `activity.scripts_min_files` (default `3`) script files, so a tiny repository stays `junk`.
- `classify` needs the manifest kinds and the per-language lines: pass them from `cli.scan_one` (they are in
  `facts` and in the metrics already).
- Reason example: `no service markers; 82% script lines in 14 files`.

`applicability.json`:

- Add `trial` and `scripts` to `_classes`.
- `guidance_classes`: add `scripts` (general rules such as `makefile-guide` still help); do not add `trial`.
- `default_rule_classes` stays `active`, `stale`. Rules that fit scripts get `"classes": ["active", "stale", "scripts"]`.

### 3. Skip the LLM by class

- `applicability.json` → `llm_skip_classes`, default `archived`, `junk`, `docs`, `trial`, `scripts`.
- `cmd_llm.select()` drops repositories in `llm_skip_classes` in every mode: `--classes`, `--repo`, and focus
  repositories from `cmd_run`.
- Each dropped repository that was selected gets an entry
  `{"repo": id, "status": "skipped", "reason": "class: trial", "head": ...}` in `llm-assessment.json`. No cache file.
- `--llm-all-classes` turns the filter off (for an explicit request on one repository).
- The summary line counts `ok`, `error`, `skipped`. Exit code is 0 when no selected repository has `error`
  (today it is 1 when no assessment is `ok`; with all focus repositories skipped that would be a false failure).

### 4. Any Git host (GitLab and GitHub)

Identity and terms:

- Replace "GitLab URL" by "repository URL" in code comments, `--help`, `README.md`, `docs/repo-scan.md` and the
  skill. Field names stay (`url_source`, `remote_key`).
- New field `forge` on each repository record and each `meta.roots` entry: `github` when the host is `github.com`
  or listed in `REPO_SCAN_GITHUB_HOSTS` / `--github-host` (GitHub Enterprise); `gitlab` when the host is listed in
  `REPO_SCAN_GITLAB_HOSTS` / `--gitlab-host` or contains `gitlab`; otherwise by CI files (`.github/workflows` →
  `github`, `.gitlab-ci.yml` → `gitlab`), else `unknown`. No network.
- Default context root above a focus repository: `<host>/<first path segment>` for every forge (GitLab group,
  GitHub owner). Unchanged code, now documented for GitHub.

CI links from GitHub Actions (`relations.py`, `manifests.py`):

- `parse_github_workflow` also returns `uses: [{ref, line}]` for job-level and step-level `uses:`.
- `owner/repo/.github/workflows/<file>@<ref>` (reusable workflow) → repository `<host>/owner/repo`, kind `ci`,
  confidence 0.95, detail `{"files": [<file>], "ref": <ref>}`.
- `owner/repo@<ref>` or `owner/repo/<path>@<ref>` (action) → repository `<host>/owner/repo`, kind `ci`,
  confidence 0.9, detail `{"action": <path or "">, "ref": <ref>}`.
- `./...` (local action or workflow) is not a link. `docker://...` is not a link.
- A reference whose `owner/repo` is outside the scanned roots counts in `stats.skipped_external_actions` (for
  example `actions/checkout`), not in `unresolved`, unless its owner is a scanned root owner; then it is
  `unresolved` with reason `outside scanned roots`, like GitLab includes.
- `<host>` is the host of the repository that holds the workflow.

Libraries:

- Git URL dependencies resolve by URL key: pip `pkg @ git+https://<host>/<path>.git@ref` and `git+ssh://`,
  poetry `{git = "..."}`, npm `github:owner/repo`, `git+https://...`, `owner/repo#ref`. Confidence 0.9, kind
  `library`, detail `{"via": "git-url"}`.
- `go.mod` already resolves by module name; add a test with `github.com/<owner>/<repo>` modules.

Other:

- `llm.py`: add the first `.github/workflows/*.yml` (sorted) to the excerpts; bump `PROMPT_VERSION`.
- ArgoCD `repoURL` on github.com already works; add a test.
- The wrapper and `defaults.env` need no change: `REPO_SCAN_ROOTS` and `REPO_SCAN_ROOT_URLS` take any host.

### 5. Wrapper and skill

- No new wrapper command. Document two flows in `tools/repo-scan/skill/repo-scan/SKILL.md`:
  - one repository: `repo-scan.sh run <repo> --write-repo-artifacts`;
  - all roots: `repo-scan.sh scan` first, report counts by class and how many stage 2 will skip, then
    `repo-scan.sh run --write-repo-artifacts`.
- `--write-repo-artifacts` still needs the user's consent (it writes into every listed repository).
- The report lists skipped repositories by class.
- A company copy of the skill (with its own `defaults.env`) is updated outside this public repository.

## Files to change

| File | Change |
|---|---|
| `tools/repo-scan/reposcan/cli.py` | slice writer and helper, `cmd_run` stage 2 write-back, `select()` skip, `--llm-all-classes`, `--github-host`, `--gitlab-host`, help texts |
| `tools/repo-scan/reposcan/discover.py` | `classify`: `trial`, `scripts`; `forge` |
| `tools/repo-scan/reposcan/manifests.py` | `uses:` in `parse_github_workflow`; git URL dependencies |
| `tools/repo-scan/reposcan/relations.py` | GitHub `ci` edges, git URL `library` edges, `skipped_external_actions` |
| `tools/repo-scan/reposcan/llm.py` | `skipped` entries, workflow excerpt, `PROMPT_VERSION` |
| `tools/repo-scan/applicability.json` | `trial_*`, `scripts_*`, `slice_classes`, `llm_skip_classes`, `_classes`, `guidance_classes` |
| `tools/repo-scan/reposcan/__init__.py` | tool `VERSION` |
| `tests/repo_scan/test_repo_scan.py`, `tests/repo_scan/fixtures/` | see Tests |
| `tools/repo-scan/README.md`, `docs/repo-scan.md`, `tools/repo-scan/skill/repo-scan/SKILL.md` | behavior, outputs, classes, hosts |
| `CHANGELOG.md`, `UPGRADE.md`, `Cargo.toml`, `package.json`, `Cargo.lock` | `v3.0.0`, `Breaking:` entry, migration |

## Tests

Fixtures (in the temporary `work/<host>/...` tree the tests already build):

- `work/gitlab.example.com/team/demo-app` (trial), `.../team/ops-scripts` (shell and loose Python, CI, 300+ lines,
  no Dockerfile or package), `.../team/service-autotests` (stays `active`).
- `work/github.com/example-org/`: `service` with `.github/workflows/ci.yml` using
  `example-org/shared-workflows/.github/workflows/build.yml@v1`, `example-org/setup-action@v2` and
  `actions/checkout@v4`; `shared-workflows`; `setup-action`; a Go library `lib` used by `service` via `go.mod`;
  a Python dependency `lib2 @ git+https://github.com/example-org/lib2.git@v1`.

Checks:

- Classes and reasons for `trial`, `scripts`, autotests.
- Fake `claude` (`AGENTIC_LLM_CLAUDE_BIN`) is not called for skip classes in focus mode and with `--repo`; entries
  are `skipped`; `--llm-all-classes` calls it; exit code rules.
- Focus `run --write-repo-artifacts`: six files, no `local_path`, edges equal to `OUT/relationships.json`, old
  files removed, `git status --porcelain` empty, `.agentic/` in `.git/info/exclude`.
- Scan of all roots with the flag: slices only for `slice_classes`.
- GitHub: ids, `forge`, two `ci` edges with confidences 0.95 and 0.9, `skipped_external_actions` = 1, `library`
  edges for `go.mod` and the git URL, ArgoCD `repoURL` on github.com.
- Existing tests keep passing after the test of the old file layout is rewritten.

## Verification

```bash
make test-repo-scan
make test
make lint
# manual, with consent (writes .agentic/ into the clones):
bash tools/repo-scan/skill/repo-scan/scripts/repo-scan.sh run ~/work/<host>/<group>/team/service --write-repo-artifacts
ls ~/work/<host>/<group>/team/service/.agentic/repo-scan/
git -C ~/work/<host>/<group>/team/service status --porcelain
bash tools/repo-scan/skill/repo-scan/scripts/repo-scan.sh scan   # counts by class; check reasons of 3-5 trial/scripts repos
```

## Open questions

- Final lists `trial_names`, `trial_patterns`, `trial_exclude` after a scan of real roots.
- `scripts_min_ratio` and `scripts_min_files` thresholds after the same scan.
- Whether `scripts` repositories need their own rule set in `applicability.json`.
