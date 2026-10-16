---
name: experiment-tracking
description: "Applies an MLflow tracking pattern for reproducible ML experiments; use when running training experiments, comparing runs, or reproducing a historical experiment."
---

# Skill: Experiment Tracking (MLflow)

## When to load

When running training experiments, comparing runs, or reproducing a historical experiment.

## MLflow Tracking Pattern

```python
with mlflow.start_run(run_name="xgboost-lr-0.01-depth-6") as run:
    mlflow.log_params({
        "model_type": "xgboost",
        "learning_rate": 0.01,
        "max_depth": 6,
        "data_version": dataset_version,
        "random_seed": 42,
    })
    mlflow.set_tags({
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip(),
    })

    model = train_model(X_train, y_train, hyperparams)

    mlflow.log_metrics({"test_auc_roc": 0.847, "test_f1": 0.731})

    signature = mlflow.models.infer_signature(X_train, model.predict(X_train))
    mlflow.xgboost.log_model(model, "model", signature=signature)
    mlflow.log_artifact("evaluation_scorecard.json")
```
