---
description: Dataset split, leakage, and feature parity constraints for ML training code.
paths:
  - "**/training/**"
  - "**/features/**"
  - "**/*.ipynb"
---

# ML data integrity

- Use the test split once, for the final candidate evaluation; never tune hyperparameters on it.
- Split time-series data by a time `column`; do not shuffle future rows into the training set.
- Define each feature once in shared code that both the training job and the inference service import.
- Remove any feature `column` that is derived from the target or is not available at prediction time.
- Document the source table and computation of every feature in the feature definition file.
