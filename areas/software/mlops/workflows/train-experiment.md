---
name: train-experiment
type: workflow
trigger: /train-experiment
description: Run a reproducible model training experiment with full environment snapshot and automatic evaluation.
inputs:
  - model_name
  - training_config
outputs:
  - trained_model_artifact
  - evaluation_scorecard
roles:
  - developer
  - qa
execution:
  initiator: developer
agent: developer
related-rules:
  - reproducibility.md
  - data-integrity.md
uses-skills:
  - experiment-tracking
  - feature-engineering
quality-gates:
  - environment fully snapshotted before training starts
  - training loss decreased monotonically
  - model artifact logged to MLflow with all metadata
---

## Steps

### 1. Prerequisites Validation — `@developer`
- **Input:** model name, config YAML
- **Actions:** confirm data version exists and quality checks passed; verify training config YAML is valid; check compute resource budget
- **Output:** validation confirmation
- **Done when:** all prerequisites met; no blockers

### 2. Environment Snapshot — `@developer`
- **Input:** validated prerequisites
- **Actions:** log git commit hash; build/verify training Docker image digest; register data snapshot version in MLflow
- **Output:** immutable environment record in MLflow run
- **Done when:** snapshot logged; run is reproducible from this state

### 3. Training Run — `@developer`
- **Input:** snapshotted environment
- **Actions:** submit job to training cluster; stream training logs; surface loss curves in real-time; monitor for anomalies (NaN loss, divergence)
- **Output:** completed training run; model artifact in MLflow
- **Done when:** all epochs completed; loss decreased; artifact logged

### 4. Validation — `@qa`
- **Input:** completed run
- **Actions:** confirm training loss decreased monotonically; verify model artifact logged correctly; run `/evaluate-model` automatically; compare against current champion
- **Output:** evaluation scorecard; comparison vs. top 3 previous runs
- **Done when:** evaluation complete; recommendation produced (promote / continue tuning / investigate)

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /train-experiment"])
  role_1["developer"]
  role_2["qa"]
  step_1["1. Prerequisites Validation"]
  step_2["2. Environment Snapshot"]
  step_3["3. Training Run"]
  step_4["4. Validation"]
  exit(["Logged artifact + evaluation scorecard + champion comparison = experiment c..."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> exit
  role_1 -. owns .-> step_1
  role_1 -. owns .-> step_2
  role_1 -. owns .-> step_3
  role_2 -. owns .-> step_4
```
<!-- agent-diagram:end -->

## Exit
Logged artifact + evaluation scorecard + champion comparison = experiment complete.

**Next:** /evaluate-model — evaluate the trained candidate.
