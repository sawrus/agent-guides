---
workflow: evaluate-model
---

# Prompt: `/evaluate-model`

Use when: evaluating a trained model against a held-out test set, current champion, and business/fairness constraints before promotion.

---

## Example 1 — Binary classification promotion review

**EN:**
```
/evaluate-model

Run ID: mlflow://fraud-exp/8124ac91
Champion reference: fraud-detection-xgb-v12 (Production)
Model type: binary classification
Held-out test set: fraud_eval_2026_02_15.parquet (never used in training)
Required metrics:
- AUC-ROC, PR-AUC, precision, recall, F1 at operating threshold 0.72
- confusion matrix for amounts > $500 and <= $500
Business translation:
- estimate prevented fraud dollars/month at current traffic
- estimate false-positive manual review cost increase
Fairness check required: disparity across customer_region and account_age_bucket
Decision options: PROMOTE / DO_NOT_PROMOTE / NEEDS_REVIEW
Output: signed evaluation_scorecard.json + plots + champion comparison summary
```

**RU:**
```
/evaluate-model

Run ID: mlflow://fraud-exp/8124ac91
Champion reference: fraud-detection-xgb-v12 (Production)
Тип модели: binary classification
Held-out test set: fraud_eval_2026_02_15.parquet (никогда не использовался в обучении)
Обязательные метрики:
- AUC-ROC, PR-AUC, precision, recall, F1 на operating threshold 0.72
- confusion matrix для сумм > $500 и <= $500
Бизнес-интерпретация:
- оценить предотвращённые fraud losses в месяц при текущем трафике
- оценить рост стоимости ручной проверки из-за false positive
Требуется fairness check: disparity по customer_region и account_age_bucket
Варианты решения: PROMOTE / DO_NOT_PROMOTE / NEEDS_REVIEW
Результат: подписанный evaluation_scorecard.json + графики + summary сравнения с champion
```

---

## Example 2 — Regression model with champion comparison and leakage guard

**EN:**
```
/evaluate-model

Run ID: mlflow://pricing-exp/cd09f552
Champion reference: price-forecast-lgbm-v7
Model type: regression
Held-out test set: demand_forecast_eval_week_10 (data version dv_2026_03_01)
Checks required:
- verify test set rows were excluded from every training iteration and hyperparameter search
- compute MAE, RMSE, R2, and MAPE vs champion on the same horizon
- business impact: estimate inventory carrying cost delta if challenger replaces champion
- slice analysis: top 20 SKUs, long-tail SKUs, promo periods, holiday periods
Promotion rule: only recommend PROMOTE if MAE improves and no slice regresses by more than 3%
Output: scorecard, leakage verification note, and decision rationale for pricing team review
```

**RU:**
```
/evaluate-model

Run ID: mlflow://pricing-exp/cd09f552
Champion reference: price-forecast-lgbm-v7
Тип модели: regression
Held-out test set: demand_forecast_eval_week_10 (версия данных dv_2026_03_01)
Требуемые проверки:
- подтвердить, что строки test set были исключены из всех итераций обучения и hyperparameter search
- вычислить MAE, RMSE, R2 и MAPE vs champion на том же горизонте
- бизнес-эффект: оценить дельту стоимости хранения запасов, если challenger заменит champion
- slice analysis: top 20 SKU, long-tail SKU, promo periods, holiday periods
Правило продвижения: рекомендовать PROMOTE только если MAE улучшается и ни один slice не деградирует более чем на 3%
Результат: scorecard, заметка о проверке leakage и обоснование решения для review командой pricing
```
