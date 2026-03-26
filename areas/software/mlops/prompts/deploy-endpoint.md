---
workflow: deploy-endpoint
---

# Prompt: `/deploy-endpoint`

Use when: deploying a model endpoint through shadow, canary, and full rollout with explicit rollback thresholds.

---

## Example 1 — Deploy new fraud model with shadow and canary

**EN:**
```
/deploy-endpoint

Model name: fraud-detection-xgb
Run ID: mlflow://fraud-prod/4f2d71b9
Deployment strategy: shadow -> canary -> full rollout
Preconditions:
- /evaluate-model scorecard recommendation = PROMOTE
- model registry approval recorded by risk lead
- current production endpoint fraud-score-v12 healthy for last 7 days
Traffic plan:
- shadow for 48h with 100% mirrored requests, no user-visible responses from challenger
- canary 5% -> 20% -> 50% -> 100% if latency p99 < 120ms and error rate < 0.5%
Monitoring:
- compare prediction distribution vs champion
- alert on PSI > 0.2 for any top-10 feature
- auto-rollback on SLO breach or schema mismatch in payloads
Output: deployment plan, rollout checkpoints, rollback commands, and post-deploy monitoring checklist
```

**RU:**
```
/deploy-endpoint

Model name: fraud-detection-xgb
Run ID: mlflow://fraud-prod/4f2d71b9
Стратегия деплоя: shadow -> canary -> full rollout
Предусловия:
- рекомендация в scorecard от /evaluate-model = PROMOTE
- approval в model registry зафиксирован risk lead
- текущий production endpoint fraud-score-v12 здоров последние 7 дней
План трафика:
- shadow 48ч со 100% зеркалированием запросов, без user-visible ответов от challenger
- canary 5% -> 20% -> 50% -> 100% если latency p99 < 120ms и error rate < 0.5%
Мониторинг:
- сравнивать распределение предсказаний vs champion
- алерт при PSI > 0.2 для любого из top-10 признаков
- auto-rollback при нарушении SLO или schema mismatch в payload'ах
Результат: план деплоя, rollout checkpoints, rollback commands и чеклист post-deploy мониторинга
```

---

## Example 2 — Emergency redeploy after endpoint infrastructure drift

**EN:**
```
/deploy-endpoint

Model name: recommendations-transformer
Run ID: mlflow://reco-prod/9a17cb21
Deployment strategy: canary only (skip shadow because the same artifact was already shadow-tested last week)
Context:
- current live endpoint lost autoscaling configuration during cluster migration
- no model change, but serving container and HPA manifests must be re-applied safely
Success criteria:
- 100% traffic restored on the same model artifact
- canary stages complete without error rate increase above 0.2%
- dashboards updated with new pod labels and endpoint version tags
Output: infrastructure validation checklist, canary plan, and evidence that registry state still points to the same Production artifact
```

**RU:**
```
/deploy-endpoint

Model name: recommendations-transformer
Run ID: mlflow://reco-prod/9a17cb21
Стратегия деплоя: только canary (без shadow, потому что тот же артефакт уже проходил shadow на прошлой неделе)
Контекст:
- текущий live endpoint потерял autoscaling configuration во время миграции кластера
- модель не меняется, но serving container и HPA manifests нужно безопасно применить заново
Критерии успеха:
- 100% трафика восстановлено на том же model artifact
- canary стадии завершаются без роста error rate выше 0.2%
- dashboards обновлены с новыми pod labels и endpoint version tags
Результат: чеклист валидации инфраструктуры, canary plan и доказательство, что registry state по-прежнему указывает на тот же Production artifact
```
