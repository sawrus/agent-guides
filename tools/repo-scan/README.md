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

## Commands

```bash
# Stage 1: static scan
python3 tools/repo-scan/repo_scan.py scan ~/work/<host>/<group> [more roots] --out OUT
make repo-scan REPO_SCAN_ROOTS="~/work/<host>/<group>" REPO_SCAN_OUT=/tmp/scan

# Optional: also write .agentic/repo-scan.json and .agentic/dependencies.json into every repository.
# `.agentic/` is added to .git/info/exclude. Nothing is committed.
python3 tools/repo-scan/repo_scan.py scan ROOT --out OUT --write-repo-artifacts

# Quality gate candidates (.agent/gate.json for extensions/codex/hooks/gate/gate.py); nothing runs
python3 tools/repo-scan/repo_scan.py gate-propose --in OUT            # all active+stale repos -> OUT/gate-proposals.json
python3 tools/repo-scan/repo_scan.py gate-propose PATH... --out DIR    # selected repositories

# RUNS the candidate commands in the named repositories only, keeps passing ones,
# writes .agent/gate.json locally and adds it to .git/info/exclude
python3 tools/repo-scan/repo_scan.py gate-verify PATH... [--timeout 600] [--no-write] [--out DIR]

# Stage 2: LLM assessment over stage-1 output
python3 tools/repo-scan/repo_scan.py llm --in OUT --provider claude --model haiku --repo rule-engine --repo apiutil
python3 tools/repo-scan/repo_scan.py llm --in OUT --provider claude --model sonnet --classes active --limit 5
AGENTIC_LLM_API_KEY=... python3 tools/repo-scan/repo_scan.py llm --in OUT --provider litellm --repo rule-engine
```

`--now ISO8601` fixes the reference time of the activity window (tests use it). `--no-scc` forces the built-in
counter. `--jobs N` sets parallel workers (default 8).

## Stage 1 outputs (`--out`)

| File | Content |
|---|---|
| `repositories.json` | One record per repository: id (`<host>/<path>`), expected URL, `remote get-url origin` (credentials removed) and `url_verified`, HEAD, commits in the window, activity class with reasons, languages and lines, top-level entries, `AGENTS.md` / `CLAUDE.md` / `.agent/`, Makefile targets, CI jobs and includes, manifests (pyproject with poetry sources, requirements, package.json, go.mod, Dockerfile, compose, Helm, ArgoCD, env keys), published packages, Kafka topics, gRPC protos. |
| `relationships.json` | `edges[{from, to, kind, confidence, detail, evidence[{repo, path, line|key}]}]`, `unresolved[{from, kind, ref, reason, evidence}]`, `stats`. |
| `guide-applicability.json` | Per repository: `rules` and `workflows` with `id`, `path`, `confidence`, `because` (rule ids) and evidence; `task_routing` (see below); `guide_ids` lists every known id. |
| `graph.mmd` | Mermaid graph of repositories that have edges, colored by activity class. |

Repository id: the path `~/work/<host>/<path>` maps to `https://<host>/<path>`. The host segment is the one equal
to the remote host; otherwise the last domain-like segment of the scan root (so `/home/first.last/...` is not a host).

### Activity classes

Rules live in `applicability.json` → `activity`:

- `archived`: a path segment such as `archive`.
- `junk`: a path segment such as `maintenance` (for example `maintenance/bash-scripts`), a `gitlab-profile`
  repository, no readable HEAD, or no CI and fewer than 100 code+config lines.
- `active`: at least 1 commit in 365 days and CI, or at least 5 commits without CI.
- `stale`: everything else.

### Relationship kinds

| Kind | Source | Resolution |
|---|---|---|
| `library` | pyproject/requirements/package.json/go.mod dependencies; Python imports | package name → repository that publishes it (`[tool.poetry] name`, `setup.py`, non-private `package.json`, `go.mod module`). Imports count only for modules named after a published package. Dependency + import → 0.95, dependency → 0.85, import only → 0.6. A dependency from a private poetry source without a publishing repository → `unresolved`. |
| `http` | `*_ENDPOINT`, `*_URL`, `*_URI` keys in env files, compose/values YAML, `os.getenv(...)`, pydantic `BaseSettings` fields | key without env prefix/suffix (`PROD_RULE_CATALOG_ENDPOINT` → `rule-catalog`) and the first label of the URL host → repository name, package name, Makefile `APPLICATION`, or the single Helm chart name. Key and host agree → 0.9, host → 0.75, key → 0.7. Infrastructure keys (database, Redis, Kafka, S3, Sentry, ...) are counted in `stats.skipped_infra_endpoints`. |
| `kafka` | `*TOPIC*` env keys, `KafkaConsumer(...)`, `.subscribe(...)`, `.send(...)`, `topic=...` literals (non-test files of repositories that use Kafka) | one topic in two repositories. Consumer → producer is `consumes-from` (0.8). Unknown roles → `direction: unknown` (0.5). A topic seen in one repository → `unresolved`. |
| `grpc` | `.proto` services, `*Stub(` / `New*Client(` clients, `add_*Servicer_to_server` / `Register*Server` servers | client → server repository (0.8) or the only repository with the proto (0.6). |
| `ci` | `.gitlab-ci.yml` `include: project:` | project path on the same host → repository (0.95). Projects outside the scanned roots → `unresolved` with reason `outside scanned roots`. |
| `deploy` | ArgoCD `Application` `repoURL` | URL → repository (0.9). |

When several repositories match, a single `active`/`stale` candidate wins over archived or junk copies. Otherwise
the link is `unresolved` with reason `ambiguous` and the candidates.

## Guide applicability

`applicability.json` holds declarative rules. Each rule has an `id`, a `when` condition, a `confidence`, and the
agent-guides ids it enables. Ids are paths under `areas/`: `software/backend/develop-feature` is
`areas/software/backend/workflows/develop-feature.md`; `software/general/makefile-guide` is
`areas/software/general/rules/makefile-guide.md`. The tool rejects unknown ids at start.

Conditions: `all`, `any`, `not`, `code_lines`, `language` + `min_lines`, `manifest` (`makefile`, `gitlab-ci`,
`github-actions`, `dockerfile`, `docker-compose`, `helm`, `argocd`, `proto`, `pyproject`, `package-json`, `go-mod`,
`requirements`, `env`), `dependency` (regex over declared packages), `file` (glob over tracked files),
`make_target`, `activity`, `agents` (`agents_md`, `claude_md`, `agent_dir`), `relationship` + `direction`.

Repository applicability and task routing are separate:

- `rules` / `workflows`: what fits the repository at all. Only `guidance_classes` (`active`, `stale`) get guidance.
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
- `litellm`: OpenAI-compatible `POST <base>/v1/chat/completions`. `AGENTIC_LLM_BASE_URL` (default
  `https://llm.dats.services/`), `AGENTIC_LLM_API_KEY` (required, read only from the environment, never written),
  `AGENTIC_LLM_MODEL` or `--model` (default `coding-agent-default`; a `dats_ai/` OpenCode prefix is removed).

## Tests

`make test-repo-scan` (part of `make test`) builds four linked repositories from `tests/repo_scan/fixtures` in a
temporary `work/gitlab.example.com/team/...` tree and checks discovery, URL mapping, classes, edges with evidence,
unresolved links, secret handling, applicability ids, repository artifacts, gate commands, both LLM providers
(fake `claude` binary and a local HTTP stub), cache, and `scc` use.

## Limits

- Call analysis is regex based. Dynamic topic names, URLs built in code, and clients generated at build time are
  not seen. Semgrep rules are the next step.
- YAML is read line by line (no YAML library). Anchors, `extends`, and multi-document tricks in CI are not expanded.
- Helm templates and vendored subcharts are skipped for env keys; values files are read.
