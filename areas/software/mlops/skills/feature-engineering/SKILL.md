---
name: feature-engineering
description: "Builds declarative feature pipelines and prevents training-serving skew; use when building training datasets, designing feature pipelines, or debugging training-serving skew."
---

# Skill: Feature Engineering

## When to load

When building training datasets, designing feature pipelines, or debugging training-serving skew.

## Declarative Feature Pipeline

```python
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer

preprocessor = ColumnTransformer(transformers=[
    ('num', Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
    ]), numeric_features),
    ('cat', Pipeline([
        ('imputer', SimpleImputer(strategy='constant', fill_value='unknown')),
        ('encoder', OneHotEncoder(handle_unknown='ignore', sparse_output=False)),
    ]), categorical_features),
])

# ✅ Fit ONLY on training data
preprocessor.fit(X_train)
X_train_processed = preprocessor.transform(X_train)
X_test_processed = preprocessor.transform(X_test)  # Uses train statistics
```

## Training-Serving Skew Prevention

```python
# Single feature definition used in BOTH training and inference
def compute_user_features(user_id: str, reference_date: datetime) -> dict:
    """
    Used by: training pipeline (historical dates) AND inference API (current date).
    Identical computation guarantees no skew.
    """
    orders = db.query("SELECT * FROM orders WHERE user_id = %s AND created_at < %s", (user_id, reference_date))
    return {
        "order_count_30d": count_in_window(orders, reference_date, days=30),
        "avg_order_value_90d": avg_in_window(orders, reference_date, days=90),
    }
```
