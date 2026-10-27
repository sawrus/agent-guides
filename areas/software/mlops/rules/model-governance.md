---
description: Model registry, evaluation, approval, and model card requirements before a model serves traffic.
paths:
  - "**/models/**"
  - "**/serving/**"
  - "**/mlflow*"
  - "**/model_card*.md"
---

# Model governance

- Register every production model in the model registry and promote it only through registry stage transitions.
- Do not deploy a model with an ad hoc script or `command` that bypasses the registry.
- Compare a candidate with the current production model on the held-out test set and store the evaluation metrics with the registry version.
- Require a named human approval on the registry version before promotion.
- Record who deployed, when, which registry version, and the rollback version for every production deployment.
- Add a model card with intended use, metrics per subgroup, known limitations, and bias assessment.
