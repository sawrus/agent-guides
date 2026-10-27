---
covers:
  - tools/repo-scan/**
---

# Repository analysis (repo-scan)

`tools/repo-scan` scans many local Git repositories and answers two questions:

1. Which agent-guides workflows and rules fit each repository?
2. How do the repositories depend on each other (libraries, HTTP, Kafka, gRPC, CI includes, ArgoCD)?

Stage 1 is static and offline. It never runs code of the analyzed repositories and never commits to them.
Each link and recommendation keeps evidence (path plus line or key) and a confidence. Links with confidence of at
least 0.8 (`--trusted-min`) are `trusted`. Links that do not resolve to exactly one repository are listed as
`unresolved`. Secret values are not stored.

Repositories are identified by their GitLab URL (`https://<host>/<group>/.../<repo>`), not by a local path. The URL
is inferred from `~/work/<host>/<path>` or set per root with `--root-url <dir>=<url>`. Activity classes are
`active`, `stale`, `docs`, `archived`, `junk`.

```bash
python3 tools/repo-scan/repo_scan.py run ROOTS --out OUT          # scan + LLM in one command
python3 tools/repo-scan/repo_scan.py run ~/work/<host>/<group>/team/service --out OUT   # one repository, links resolved
make repo-scan-check            # python3 >= 3.11 and git; offers to install scc
make repo-scan-tools            # optional tools: scc (default), REPO_SCAN_TOOLS='scc semgrep'
make repo-scan REPO_SCAN_ROOTS="~/work/<host>/<group-a> ~/work/<host>/<group-b>" REPO_SCAN_OUT=/tmp/scan
python3 tools/repo-scan/repo_scan.py scan ~/work/a --root-url ~/work/a=https://gitlab.example.com/team --out /tmp/scan
python3 tools/repo-scan/repo_scan.py gate-propose --in /tmp/scan
python3 tools/repo-scan/repo_scan.py llm --in /tmp/scan --provider claude --model haiku --limit 5
```

Outputs: `repositories.json`, `relationships.json`, `guide-applicability.json`, `graph.mmd`, and optionally
`gate-proposals.json` and `llm-assessment.json`.

Repository applicability is separate from task routing. `task_routing` only orders candidate workflows per task
kind; JEV still chooses the workflow for a concrete task. The relationship graph is an input for cross-project
work. `tools/repo-scan/applicability.json` names rules and workflows by their current pack ids
(`<area>/<spec>/<name>`); when the pack removes or renames an artifact, the same change updates these ids.

Details, rule format, relationship kinds and limits: [tools/repo-scan/README.md](../tools/repo-scan/README.md).
