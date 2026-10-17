---
name: model-monitoring
description: "Defines model monitoring dimensions and PSI-based drift detection; use when setting up monitoring for a deployed model or responding to drift alerts."
---

# Skill: Model Monitoring

## When to load

When setting up monitoring for a deployed model or responding to drift alerts.

## Monitoring Dimensions

```
1. Operational health
   - Latency: p50, p95, p99
   - Error rate: prediction failures, input validation failures

2. Data drift (vs training baseline)
   - PSI (Population Stability Index) per feature
   - PSI > 0.2 = significant shift → retrain likely needed

3. Model quality (when labels available)
   - Accuracy metrics after ground truth arrives
   - Business outcome correlation
```

## PSI Drift Detection

```python
def calculate_psi(expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
    """PSI < 0.1: stable. 0.1-0.2: monitor. > 0.2: retrain."""
    breakpoints = np.percentile(expected, np.linspace(0, 100, buckets + 1))
    exp_counts = np.clip(np.histogram(expected, breakpoints)[0] / len(expected), 1e-4, None)
    act_counts = np.clip(np.histogram(actual, breakpoints)[0] / len(actual), 1e-4, None)
    return np.sum((act_counts - exp_counts) * np.log(act_counts / exp_counts))
```
