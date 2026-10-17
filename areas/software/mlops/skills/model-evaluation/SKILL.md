---
name: model-evaluation
description: "Guides model evaluation with threshold selection and subgroup fairness analysis; use when evaluating a trained model, comparing model versions, or performing fairness analysis."
---

# Skill: Model Evaluation

## When to load

When evaluating a trained model, comparing versions, or performing fairness analysis.

## Threshold Selection

```python
def select_optimal_threshold(y_true, y_prob, business_objective: str):
    """
    business_objective:
    - 'max_f1': balanced precision/recall
    - 'high_precision': minimize false positives (fraud)
    - 'high_recall': minimize false negatives (screening)
    """
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_prob)
    if business_objective == 'max_f1':
        f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-8)
        return thresholds[np.argmax(f1_scores)]
```

## Subgroup Fairness Analysis (Required for People-Affecting Models)

```python
def evaluate_fairness(y_true, y_pred, sensitive_attribute):
    groups = sensitive_attribute.unique()
    results = {g: {
        "n": (sensitive_attribute == g).sum(),
        "positive_rate": y_pred[sensitive_attribute == g].mean(),
        "tpr": recall_score(y_true[sensitive_attribute == g], y_pred[sensitive_attribute == g]),
    } for g in groups}

    pos_rates = [r["positive_rate"] for r in results.values()]
    dp_diff = max(pos_rates) - min(pos_rates)

    if dp_diff > 0.1:
        logger.warning(f"Demographic parity difference {dp_diff:.3f} exceeds 0.1 threshold")
    return results, dp_diff
```
