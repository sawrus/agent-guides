---
workflow: train-experiment
---

# Prompt: `/train-experiment`

Use when: running a reproducible model training experiment with a pinned environment, tracked artifacts, and automatic evaluation against the champion.

---

## Example 1 — Retrain fraud model on fresh quarterly data

**EN:**
```
/train-experiment

Model name: fraud-detection-xgb
Training config: configs/fraud_xgb_q2_2026.yaml
Data version: dv_2026_03_15_fraud_training
Compute budget: 1 GPU not required, max 16 CPU cores, training must finish in < 3 hours
Requirements:
- snapshot git commit, Docker image digest, and feature store version in MLflow before training
- run hyperparameter search over max_depth, eta, min_child_weight, and scale_pos_weight
- stop immediately if validation loss diverges or NaN metrics appear
- after training, run /evaluate-model automatically against current champion fraud-detection-xgb-v12
Output: MLflow run link, model artifact URI, best config summary, and evaluation handoff
```

**RU:**
```
/train-experiment

Model name: fraud-detection-xgb
Training config: configs/fraud_xgb_q2_2026.yaml
Версия данных: dv_2026_03_15_fraud_training
Бюджет compute: GPU не требуется, максимум 16 CPU cores, обучение должно завершиться < 3 часов
Требования:
- до обучения зафиксировать git commit, Docker image digest и версию feature store в MLflow
- запустить hyperparameter search по max_depth, eta, min_child_weight и scale_pos_weight
- немедленно остановить обучение, если validation loss расходится или появляются NaN метрики
- после обучения автоматически запустить /evaluate-model против текущего champion fraud-detection-xgb-v12
Результат: ссылка на MLflow run, URI model artifact, summary лучшей конфигурации и handoff в evaluation
```

---

## Example 2 — Experiment after data quality recovery

**EN:**
```
/train-experiment

Model name: demand-forecast-lstm
Training config: configs/demand_lstm_recovery.yaml
Context: previous two runs used corrupted holiday calendar features; data quality incident fixed yesterday
Prerequisites:
- confirm corrected feature table passed quality checks and matches data version dq_fix_2026_03_24
- compare new run not only with champion but also with the two bad runs to prove recovery
- keep full environment reproducibility because finance team may audit this retrain
Success criteria:
- training loss decreases monotonically across all epochs
- evaluation scorecard includes top-3 previous runs comparison
- run metadata clearly marks this as post-incident remediation training
Output: reproducibility record, training summary, and recommendation whether to proceed to deploy-endpoint or continue tuning
```

**RU:**
```
/train-experiment

Model name: demand-forecast-lstm
Training config: configs/demand_lstm_recovery.yaml
Контекст: предыдущие два запуска использовали повреждённые holiday calendar features; data quality incident исправлен вчера
Предусловия:
- подтвердить, что исправленная feature table прошла quality checks и соответствует версии данных dq_fix_2026_03_24
- сравнить новый run не только с champion, но и с двумя неудачными run'ами, чтобы доказать восстановление
- сохранить полную воспроизводимость окружения, потому что finance team может аудировать этот retrain
Критерии успеха:
- training loss монотонно уменьшается на всех эпохах
- evaluation scorecard включает сравнение с top-3 previous runs
- metadata run'а явно помечает его как post-incident remediation training
Результат: запись о воспроизводимости, summary обучения и рекомендация, переходить ли к deploy-endpoint или продолжать tuning
```
