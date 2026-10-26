---
name: repo-scan
description: Analyze one or many local Git repositories with agent-guides tools/repo-scan - activity class, metrics, dependency graph between repositories (libraries, HTTP, Kafka, gRPC, CI, deploy) with evidence, agent-guides applicability, quality gate candidates, and an optional LLM assessment. Use when the user asks to "scan repositories", "analyze repo dependencies", "who depends on this service", "is agent-guides applicable", "build a dependency graph", or "propose gate.json".
---

# repo-scan

Runs `tools/repo-scan` of agent-guides through the wrapper `<skill base>/scripts/repo-scan.sh` (path relative to
this skill's directory). The wrapper finds agent-guides (or clones it), checks requirements, applies the settings
and calls the tool.

- Stage 1 (`scan`) is static and offline. It never runs code of the analyzed repositories and never commits to them.
- Stage 2 (`llm`) sends the stage 1 summary and short excerpts (README, Makefile, CI) to an LLM.
- `run` does both stages in one command.

## Parameters (ask the user when unclear)

| User asks for | Command |
|---|---|
| one repository, both stages | `repo-scan.sh run <repo dir>` |
| one repository, static only | `repo-scan.sh scan <repo dir>` |
| many repositories, both stages | `repo-scan.sh run [<group dir> ...]` (no arguments: `REPO_SCAN_ROOTS`) |
| many repositories, static only | `repo-scan.sh scan [<group dir> ...]` |
| LLM over an earlier scan | `repo-scan.sh llm [<repo> ...] [--limit N]` |
| gate candidates / verification | `repo-scan.sh gate-propose [<repo> ...]` / `repo-scan.sh gate-verify <repo> ...` |

- A repository directory is the focus: the context roots (`REPO_SCAN_CONTEXT_ROOTS`, default `REPO_SCAN_ROOTS`)
  are scanned so its links resolve, and only its view is written.
- Provider: `--provider claude --model haiku|sonnet|opus` (default `claude`, model `haiku`) or
  `--provider litellm` (needs `AGENTIC_LLM_BASE_URL`, `AGENTIC_LLM_API_KEY` and a model).
- Output: `--out DIR` (default `~/.cache/agentic/repo-scan/<repo name>` or `.../all`).
- Settings live in `~/.config/agentic/repo-scan.env` (`REPO_SCAN_ROOTS`, `REPO_SCAN_ROOT_URLS`,
  `REPO_SCAN_CONTEXT_ROOTS`, `REPO_SCAN_PROVIDER`, `REPO_SCAN_MODEL`, `AGENTIC_LLM_BASE_URL`, `AGENTIC_LLM_MODEL`).

## Workflow

### Step 1 - requirements

```bash
bash <skill base>/scripts/repo-scan.sh check
```

Exit 1 means `python3` >= 3.11 or `git` is missing: show the printed install command and stop. If `scc` is
missing, offer `bash <skill base>/scripts/repo-scan.sh tools` (exact line counts); without it a built-in counter runs.

### Step 2 - scan

For many repositories run stage 1 first and report the counts:

```bash
bash <skill base>/scripts/repo-scan.sh scan [<group dir> ...]
```

For one repository use `run` directly; stage 2 then assesses only that repository:

```bash
bash <skill base>/scripts/repo-scan.sh run <repo dir>
```

### Step 3 - LLM assessment of many repositories

Stage 2 makes one LLM call per repository. Tell the user how many active repositories the scan found and ask
before running it on more than 10. Then:

```bash
bash <skill base>/scripts/repo-scan.sh llm [--limit N] [--classes active]
```

### Step 4 - report

Read the output directory and report: repositories by activity class; edges by kind and how many are trusted
(confidence >= 0.8); for a focus repository its incoming and outgoing edges with evidence (`path:line`); top
unresolved links; applicable workflows and rules; stage 2 summary and risks. Give the paths of
`repositories.json`, `relationships.json`, `guide-applicability.json`, `graph.mmd` and `llm-assessment.json`.

## Rules

- Do not pass `--write-repo-artifacts` and do not run `gate-verify` without the user's consent: the first writes
  `.agentic/` into each repository, the second runs repository commands (tests, lint).
- Never commit or push in the analyzed repositories.
- Never write `AGENTIC_LLM_API_KEY` into files; the user sets it in the environment.
- Do not guess unresolved links; report them as unresolved.
