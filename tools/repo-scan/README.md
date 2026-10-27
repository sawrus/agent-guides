# repo-scan

`repo-scan` analyzes many local Git repositories (for example all checkouts of two GitLab groups). It finds
which agent-guides workflows and rules fit each repository and how the repositories depend on each other.

- Python 3.11+ standard library only. `scc` is used for line counts when it is on `PATH`; otherwise a built-in
  counter runs over tracked files. `semgrep` is only detected (call analysis with Semgrep rules is the next step).
- Stage 1 (`scan`) is offline. It reads files and git metadata. It never runs code of the analyzed repositories:
  git runs with hooks and `core.fsmonitor` off, and no build tool is called.
- Every relationship and every recommendation carries evidence (`path` plus `line` or `key`) and a `confidence`.
  A link that cannot be resolved to exactly one repository goes to `unresolved`. The tool does not guess.
- Env files keep only key names, line numbers and URL hosts. Secret values are never stored. Local secret
  files (`.env`, `.env.local`, ...) are skipped; templates (`sample.env`, `*.env`, `.env.example`) are read.

## Requirements

| Tool | Need | Check or install |
|---|---|---|
| `python3` >= 3.11, `git` | required | `make repo-scan-check` prints the install command for your OS |
| `scc` | optional: exact line counts; without it a built-in counter runs | `make repo-scan-tools` (pinned release, checksum verified, into `~/.local/bin`) |
| `semgrep` | optional: detected only, call rules are planned | `make repo-scan-tools REPO_SCAN_TOOLS='scc semgrep'` (pipx or uv) |
| `claude` | only for `llm --provider claude` | `sh tools/repo-scan/check-tools.sh --llm-claude` |

`make repo-scan` runs the check first. On a terminal the check offers to install a missing `scc`
(`REPO_SCAN_NO_PROMPT=1` turns the offer off). The check is plain `sh`, so it also works where Python is missing.

## Commands

```bash
# Both stages in one command: scan, then the LLM assessment (focus repositories, else --classes active)
python3 tools/repo-scan/repo_scan.py run ~/work/<host>/<group> [more roots] --out OUT [--provider claude --model haiku]
python3 tools/repo-scan/repo_scan.py run ROOTS --out OUT --skip-llm          # stage 1 only

# One repository (focus mode): its links still resolve, see "Focus mode" below
python3 tools/repo-scan/repo_scan.py run ~/work/<host>/<group>/team/service --out OUT
python3 tools/repo-scan/repo_scan.py scan ROOTS --focus team/service --out OUT

# Stage 1: static scan
python3 tools/repo-scan/repo_scan.py scan ~/work/<host>/<group> [more roots] --out OUT
# Optional GitLab URL per root (repeatable); without it the URL is inferred from the path
python3 tools/repo-scan/repo_scan.py scan ~/work/gitlab.example.com/group --root-url ~/work/gitlab.example.com/group=https://gitlab.example.com/group --out OUT
# Edges with confidence >= 0.8 are trusted; change the threshold
python3 tools/repo-scan/repo_scan.py scan ROOT --out OUT --trusted-min 0.9
make repo-scan REPO_SCAN_ROOTS="~/work/<host>/<group>" REPO_SCAN_OUT=/tmp/scan

# Optional: also write .agentic/repo-scan.json and .agentic/dependencies.json into every repository.
# `.agentic/` is added to .git/info/exclude. Nothing is committed.
python3 tools/repo-scan/repo_scan.py scan ROOT --out OUT --write-repo-artifacts

# Quality gate candidates (.agent/gate.json for extensions/codex/hooks/gate/gate.py); nothing runs
python3 tools/repo-scan/repo_scan.py gate-propose --in OUT            # all active+stale repos -> OUT/gate-proposals.json
python3 tools/repo-scan/repo_scan.py gate-propose https://gitlab.example.com/group/team/service --in OUT
python3 tools/repo-scan/repo_scan.py gate-propose PATH... --out DIR    # local checkouts, no scan needed

# RUNS the candidate commands in the named repositories only, keeps passing ones,
# writes .agent/gate.json locally and adds it to .git/info/exclude
python3 tools/repo-scan/repo_scan.py gate-verify URL|PATH... [--in OUT] [--timeout 600] [--no-write] [--out DIR]

# Stage 2: LLM assessment over stage-1 output
python3 tools/repo-scan/repo_scan.py llm --in OUT --provider claude --model haiku \
  --repo https://gitlab.example.com/group/team/service --repo libs/common-lib
python3 tools/repo-scan/repo_scan.py llm --in OUT --provider claude --model sonnet --classes active --limit 5
AGENTIC_LLM_API_KEY=... python3 tools/repo-scan/repo_scan.py llm --in OUT --provider litellm --repo service
```

`--now ISO8601` fixes the reference time of the activity window (tests use it). `--no-scc` forces the built-in
counter. `--jobs N` sets parallel workers (default 8).

`--repo` (llm) and the positional arguments of the gate commands accept a GitLab URL, `host/path`, a path suffix
such as `team/service`, a repository name, or a local path. Names other than local checkouts are
looked up in `--in OUT/repositories.json`.

## Agent skill

`tools/repo-scan/skill/repo-scan/` is a skill for Claude Code, OpenCode and Codex: `SKILL.md` plus the wrapper
`scripts/repo-scan.sh` (`run`, `scan`, `llm`, `gate-propose`, `gate-verify`, `check`, `tools`). `make repo-scan-skill`
copies it to `SKILL_TARGET` (default `~/.claude/skills`) and records this checkout in
`~/.config/agentic/agent-guides-home`. Local defaults (roots, root URLs, context roots, LLM endpoint and model, never
the key) go into `~/.config/agentic/repo-scan.env`; a company copy of the skill can ship them in `defaults.env`.

## Focus mode (one or a few repositories)

A repository scanned alone cannot resolve its links: the library publisher, the HTTP peer and the CI template
live in other repositories. Focus mode scans context roots to build the index, then writes only the view of the
focus repositories: their edges and unresolved links, the focus records (`"focus": true`) plus their direct
neighbours, and applicability for the focus only. `relationships.json` lists the ids under `focus`.

- Focus: `--focus REPO` (repeatable: path, URL or short form). Roots that are repositories themselves are the
  focus by default, so `scan ~/work/<host>/<group>/team/service` is focus mode.
- Context roots, first found: `--context-root DIR` (repeatable), env `REPO_SCAN_CONTEXT_ROOTS` (space or `:`
  separated), `context_roots` in `~/.config/agentic/repo-scan.json`, else the `<host>/<group>` directory above each
  focus repository. Links to another GitLab host resolve only when its root is in the context.
- `--no-context` scans the focus alone (links to other repositories stay unresolved).
- `run` assesses only the focus repositories in stage 2, whatever their activity class.

## Identity

A repository is identified by its GitLab URL, `https://<host>/<group>/.../<repo>`, in every output:
edges (`from`, `to`), `unresolved`, evidence `repo`, `guide-applicability.json`, `graph.mmd`, and the per-repository
`.agentic/` files. The URL comes from:

1. `--root-url <dir>=<url>` for that root plus the path below the root (`url_source: root-url`);
2. otherwise the path `~/work/<host>/<path>` (`url_source: path`). The host segment is the one equal to the
   remote host; otherwise the last domain-like segment of the scan root, so `/home/first.last/...` is not a host;
3. otherwise the `origin` remote, else a `file://` URL.

`url_verified` tells whether the URL matches `git remote get-url origin`. The local checkout path is kept only in
`repositories.json` (`local_path`, `root_paths`) because the `llm` and `gate-*` stages read files from it.

## Stage 1 outputs (`--out`)

| File | Content |
|---|---|
| `repositories.json` | One record per repository: id (GitLab URL), `url_source`, `local_path`, `remote get-url origin` (credentials removed) and `url_verified`, HEAD, commits in the window, activity class with reasons, languages and lines, top-level entries, `AGENTS.md` / `CLAUDE.md` / `.agent/`, Makefile targets, CI jobs and includes, manifests (pyproject with poetry sources, requirements, package.json, go.mod, Dockerfile, compose, Helm, ArgoCD, env keys), published packages, Kafka topics, gRPC protos. |
| `relationships.json` | `edges[{from, to, kind, confidence, trusted, detail, evidence[{repo, path, line|key}]}]`, `unresolved[{from, kind, ref, reason, evidence}]`, `stats` (edges and trusted edges per kind, unresolved per reason). |
| `guide-applicability.json` | Per repository: `rules` and `workflows` with `id`, `path`, `confidence`, `because` (rule ids) and evidence; `task_routing` (see below); `guide_ids` lists every known id. |
| `graph.mmd` | Mermaid graph of repositories that have edges, labeled by URL and colored by activity class. Trusted edges are solid (`-->`), others dashed (`-.->`). |

An edge is `trusted` when its confidence is at least `--trusted-min` (default 0.8): for example dependency +
import, key + host match, consumer/producer Kafka pairs, CI includes, ArgoCD URLs. Weaker matches stay in the
graph as dashed edges; cross-project work should rely on trusted edges first.

### Activity classes

Rules live in `applicability.json` → `activity`:

- `archived`: a path segment such as `archive`.
- `junk`: a path segment such as `maintenance` (for example `maintenance/bash-scripts`), no readable HEAD, or no
  CI and fewer than 100 code+config lines.
- `docs`: a `gitlab-profile` repository, or a documentation-only repository: at least 2 Markdown/reST/AsciiDoc files
  and 20 documentation lines, at most 200 code+config lines, and at least twice as many documentation lines as
  code+config lines. A single README (such as the GitLab template of an empty project) does not count.
  Such repositories get only the `documentation` rule (rules and workflows marked `"classes": ["docs"]`).
- `active`: at least 1 commit in 365 days and CI, or at least 5 commits without CI.
- `stale`: everything else.

### Relationship kinds

| Kind | Source | Resolution |
|---|---|---|
| `library` | pyproject/requirements/package.json/go.mod dependencies; Python imports | package name → repository that publishes it (`[tool.poetry] name`, `setup.py`, non-private `package.json`, `go.mod module`). Imports count only for modules named after a published package. Dependency + import → 0.95, dependency → 0.85, import only → 0.6. A dependency from a private poetry source without a publishing repository → `unresolved`. |
| `http` | `*_ENDPOINT`, `*_URL`, `*_URI` keys in env files, compose/values YAML, `os.getenv(...)`, pydantic `BaseSettings` fields | key without env prefix/suffix (`PROD_CATALOG_LIB_ENDPOINT` → `catalog-lib`) and the first label of the URL host → repository name, package name, Makefile `APPLICATION`, or the single Helm chart name. Key and host agree → 0.9, host → 0.75, key → 0.7. Infrastructure keys (database, Redis, Kafka, S3, Sentry, ...) are counted in `stats.skipped_infra_endpoints`. |
| `kafka` | No central topic registry exists, so topics come from code and config: `*TOPIC*` env keys, `KafkaConsumer(...)`, `.subscribe(...)`, `.send(...)`, `topic=...` literals (non-test files of repositories that use Kafka) | one topic in two repositories. Consumer → producer is `consumes-from` (0.8). Unknown roles → `direction: unknown` (0.5). A topic seen in one repository → `unresolved`. |
| `grpc` | `.proto` services, `*Stub(` / `New*Client(` clients, `add_*Servicer_to_server` / `Register*Server` servers | client → server repository (0.8) or the only repository with the proto (0.6). |
| `ci` | `.gitlab-ci.yml` `include: project:` | project path on the same host → repository (0.95). Projects outside the scanned roots → `unresolved` with reason `outside scanned roots`. |
| `deploy` | ArgoCD `Application` `repoURL` | URL → repository (0.9). |

When several repositories match, a single `active`/`stale` candidate wins over archived or junk copies. Otherwise
the link is `unresolved` with reason `ambiguous` and the candidates.

## Guide applicability

`applicability.json` holds declarative rules. Each rule has an `id`, a `when` condition, a `confidence`, and the
agent-guides ids it enables. Optional `classes` limits a rule to activity classes (default
`default_rule_classes`: `active`, `stale`); `guidance_classes` lists the classes that get any guidance. Ids are paths under `areas/`: `software/backend/develop-feature` is
`areas/software/backend/workflows/develop-feature.md`; `software/general/makefile-guide` is
`areas/software/general/rules/makefile-guide.md`. The tool rejects unknown ids at start.

Conditions: `all`, `any`, `not`, `code_lines`, `language` + `min_lines`, `manifest` (`makefile`, `gitlab-ci`,
`github-actions`, `dockerfile`, `docker-compose`, `helm`, `argocd`, `proto`, `pyproject`, `package-json`, `go-mod`,
`requirements`, `env`), `dependency` (regex over declared packages), `file` (glob over tracked files),
`make_target`, `activity`, `agents` (`agents_md`, `claude_md`, `agent_dir`), `relationship` + `direction`.

Repository applicability and task routing are separate:

- `rules` / `workflows`: what fits the repository at all. Only `guidance_classes` (`active`, `stale`, `docs`) get
  guidance; `archived` and `junk` get none.
- `task_routing`: for each task kind (`feature`, `bugfix`, `migration`, `ci-failure`, ...) the ordered workflow
  candidates from `applicability.json` → `task_routing`, filtered to the repository's applicable workflows. It is
  a hint. The real per-task choice stays with JEV.

## Gate candidates

`gate-propose` reads the Makefile (`test`, `lint`, then `check` / `typecheck` / `test-unit`) and, when there is no
Makefile target, CI jobs named like test/lint/check whose script lines are known check commands (`pytest`,
`ruff`, `go test`, `npm test`, ...). It writes `{"commands": [...], "changelog": <CHANGELOG.md exists>, "max_blocks": 3}`,
the same format `extensions/codex/hooks/gate/gate.py` reads, plus the source line of each command.

`gate-verify` is a separate command because it executes repository code. It runs only the repositories named on
the command line, one command at a time, with a timeout (process group killed on timeout). A tracked
`.agent/gate.json` is not overwritten without `--force`.

## Stage 2: LLM

Input: the stage-1 record of the repository, its edges, its candidate guide ids, the list of all guide ids, the top-level
file list, and redacted excerpts (first 60 lines, at most 3000 characters) of `README*`, `Makefile`, `.gitlab-ci.yml`.
Redaction masks values of password/secret/token/key names, URL credentials, `sk-...`, GitLab/GitHub tokens and
private keys.

Output `llm-assessment.json`: per repository `summary`, `applicability[{id, applies, confidence, why}]`,
`missing_guides`, `risks`, `recommendations`, `gate{commands, notes}`. Ids that are not real agent-guides ids are
dropped and listed in `invalid_ids`. Results are cached in `llm-cache/` by HEAD sha, provider, model and prompt
version; `--no-cache` forces a new call.

Providers:

- `claude`: `claude -p --model haiku|sonnet|opus|fable --tools "" --no-session-persistence`, prompt on stdin,
  run in an empty temporary directory. `AGENTIC_LLM_CLAUDE_BIN` overrides the binary (tests use a fake).
- `litellm`: OpenAI-compatible `POST <base>/v1/chat/completions`. `AGENTIC_LLM_BASE_URL` (required,
  no default), `AGENTIC_LLM_API_KEY` (required, read only from the environment, never written),
  `AGENTIC_LLM_MODEL` or `--model` (default `coding-agent-default`; an OpenCode `<provider>/` prefix such as `private_llm/` is removed).

## Tests

`make test-repo-scan` (part of `make test`) builds five repositories from `tests/repo_scan/fixtures` (four linked
ones plus a docs repository) in a temporary `work/gitlab.example.com/team/...` tree and checks discovery, URL
identity, `--root-url`, trusted edges, classes including `docs`, edges with evidence,
unresolved links, secret handling, applicability ids, repository artifacts, gate commands, both LLM providers
(fake `claude` binary and a local HTTP stub), cache, and `scc` use.

## Limits

- Call analysis is regex based. Dynamic topic names, URLs built in code, and clients generated at build time are
  not seen. Semgrep rules are the next step.
- YAML is read line by line (no YAML library). Anchors, `extends`, and multi-document tricks in CI are not expanded.
- Helm templates and vendored subcharts are skipped for env keys; values files are read.
