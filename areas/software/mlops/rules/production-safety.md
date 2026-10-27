---
description: Fallback, latency, prediction logging, and drift alert requirements for model serving endpoints.
paths:
  - "**/serving/**"
  - "**/inference/**"
---

# Model serving safety

- Define a fallback for every model endpoint: a rule-based baseline, the previous model version, or a degraded response.
- Set a latency target per endpoint (for example p99 under 200 ms) and test it before release.
- Log every prediction with its input features, model version, and timestamp.
- Run high-stakes models (credit, medical, fraud) in shadow mode for at least 2 weeks before live traffic.
- Configure alerts for input feature drift and prediction drift against the training baseline.
