# CI/CD — guidance index

## What this area covers

Continuous integration and delivery pipelines: GitHub Actions, GitLab CI, quality gates, artifact management, build optimization, supply-chain security, and pipeline security hardening.

## Guidance chain

1. Project `.agent/` baseline
2. `ci-cd/rules/*` — load all
3. `ci-cd/skills/*/SKILL.md` — load only the skill matching the current task
4. `ci-cd/workflows/*` — load the workflow matching the triggered command

## Cross-cutting constraints

- **No secrets in pipeline YAML** — all credentials via vault / environment secrets, never inline.
- **Quality gates are non-negotiable** — pipelines must not merge on test failure, ever.
- **Supply-chain integrity** — pin all external actions to a full commit SHA, not a tag.
- **Artifact immutability** — built artifacts are never modified after creation; re-build instead.

## Spec map

```text
ci-cd/
├── rules/
│   ├── pipeline-standards.md         ← stage order, naming, timeout policies
│   ├── quality-gates.md              ← required checks, merge block conditions
│   └── supply-chain-security.md      ← action pinning, SBOM, provenance attestation
├── skills/
│   ├── github-actions-patterns/SKILL.md  ← reusable workflows, matrix, caching strategies
│   ├── gitlab-ci-patterns/SKILL.md       ← DAG pipelines, include templates, runners
│   ├── artifact-management/SKILL.md      ← registry push, versioning, retention policy
│   ├── build-optimization/SKILL.md       ← layer caching, parallelism, incremental builds
│   └── pipeline-security/SKILL.md        ← OIDC auth, secret scanning, SAST integration
├── workflows/
│   ├── onboard-repo.md        ← /onboard-repo
│   ├── pipeline-debug.md      ← /pipeline-debug
│   └── release-pipeline.md   ← /release-pipeline
└── prompts/
    └── *.md
```

## Discovery patterns

- `rules/*.md`
- `skills/*/SKILL.md`
- `workflows/*.md`
- `prompts/*.md`
