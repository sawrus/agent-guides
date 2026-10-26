# Repository analysis (repo-scan)

`tools/repo-scan` scans many local Git repositories and answers two questions:

1. Which agent-guides workflows and rules fit each repository?
2. How do the repositories depend on each other (libraries, HTTP, Kafka, gRPC, CI includes, ArgoCD)?

Stage 1 is static and offline. It never runs code of the analyzed repositories and never commits to them.
Each link and recommendation keeps evidence (path plus line or key) and a confidence. Links that do not resolve
to exactly one repository are listed as `unresolved`. Secret values are not stored.

```bash
make repo-scan REPO_SCAN_ROOTS="~/work/<host>/<group-a> ~/work/<host>/<group-b>" REPO_SCAN_OUT=/tmp/scan
python3 tools/repo-scan/repo_scan.py gate-propose --in /tmp/scan
python3 tools/repo-scan/repo_scan.py llm --in /tmp/scan --provider claude --model haiku --limit 5
```

Outputs: `repositories.json`, `relationships.json`, `guide-applicability.json`, `graph.mmd`, and optionally
`gate-proposals.json` and `llm-assessment.json`.

Repository applicability is separate from task routing. `task_routing` only orders candidate workflows per task
kind; JEV still chooses the workflow for a concrete task. The relationship graph is an input for cross-project
work.

Details, rule format, relationship kinds and limits: [tools/repo-scan/README.md](../tools/repo-scan/README.md).
