# MLOps — guidance index

## What this area covers

Machine learning operations: experiment tracking, model training pipelines, feature engineering, model evaluation, champion/challenger workflows, inference serving, model monitoring, and production safety gates. MLOps treats models as software artifacts with the same reproducibility and observability requirements as any production service.

## Guidance chain

1. Project `.agent/` baseline (`AGENTS.md` + `.agent/*`)
2. `.agent/rules/*` — always active
3. `.agent/rules/*` — load all for this spec
4. `.agent/skills/*/SKILL.md` — load only the skill matching the current task
5. `.agent/workflows/*` — load the workflow matching the triggered command

## Inherited from general

- SDLC methodology and handoff contracts
- Git / CI / lint and code style baselines

## MLOps-specific constraints

- Every experiment is reproducible: fixed random seed, pinned dependency versions, logged hyperparameters.
- No model promotes to production without a documented evaluation report and a champion/challenger comparison.
- Production models emit prediction latency, throughput, and data drift metrics — no silent inference.
- Training data containing PII is governed under `data-engineering/rules/pii-handling.md` at all times.

## Spec map

```text
.agent/
├── rules/
│   ├── reproducibility.md      ← seed pinning, dependency locking, artifact versioning
│   ├── data-integrity.md       ← training data lineage, validation, split discipline
│   ├── model-governance.md     ← approval gates, versioning, rollback policy
│   └── production-safety.md    ← shadow mode, canary traffic, kill switch requirements
├── skills/
│   ├── experiment-tracking/SKILL.md   ← MLflow, W&B, run comparison, artifact logging
│   ├── feature-engineering/SKILL.md   ← feature stores, transformation pipelines, leakage prevention
│   ├── model-evaluation/SKILL.md      ← metric selection, fairness checks, threshold calibration
│   ├── inference-serving/SKILL.md     ← online/batch serving, latency budgets, model registries
│   └── model-monitoring/SKILL.md      ← data drift, prediction drift, retraining triggers
├── workflows/
│   ├── train-experiment.md        ← /train-experiment
│   ├── evaluate-model.md          ← /evaluate-model
│   ├── champion-challenger.md     ← /champion-challenger
│   ├── deploy-endpoint.md         ← /deploy-endpoint
│   └── model-incident.md          ← /model-incident
└── prompts/
    └── *.md
```

## Discovery patterns

- `.agent/rules/*.md`
- `.agent/skills/*/SKILL.md`
- `.agent/workflows/*.md`
- `.agent/prompts/*.md`
