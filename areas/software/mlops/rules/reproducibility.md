---
description: Run tracking, seeds, pinned environments, and data snapshots for reproducible ML training.
paths:
  - "**/training/**"
  - "**/*.ipynb"
  - "**/conda*.yaml"
  - "**/requirements*.txt"
---

# ML reproducibility

- Log the code commit, data snapshot id, hyperparameters, and image digest of every training run before training starts.
- Set seeds for `random`, `numpy`, and the ML framework, and log the seed as a hyperparameter.
- Pin every package version in `requirements.txt` or `conda.yaml` for training and inference; do not use `>=`.
- Train only on immutable dataset snapshots, not on live tables.
- Keep a retrain command that rebuilds the model from code, data snapshot, and hyperparameters.
