---
workflow: champion-challenger
---

# Prompt: `/champion-challenger`

Use when: running a controlled champion-vs-challenger model experiment with statistical significance and rollback guardrails.

---

## Example 1 — Credit risk model challenger rollout

**EN:**
```
/champion-challenger

Champion model: credit-risk-xgb-v14 (Production in registry)
Challenger model: credit-risk-xgb-v15 (candidate from MLflow run 5d8a9f2)
Experiment duration: 14 days or until 2.5M scored applications
Primary metric: approved-loan default rate after policy thresholding
Guardrails:
- online latency p99 < 180ms
- application scoring error rate < 0.2%
- fairness disparity by age_group and region <= 0.08
Traffic split: 50% champion / 50% challenger by hashed applicant_id
Decision rules:
- promote only if default rate improves by at least 1.5% relative and p-value < 0.05
- auto-rollback if latency or fairness guardrail breaches for 30 min
Output: experiment design, sample-size calculation, daily monitoring plan, and final promotion decision template
```

**RU:**
```
/champion-challenger

Champion model: credit-risk-xgb-v14 (Production в registry)
Challenger model: credit-risk-xgb-v15 (кандидат из MLflow run 5d8a9f2)
Длительность эксперимента: 14 дней или до 2.5M скорингованных заявок
Основная метрика: default rate по одобренным займам после применения policy threshold
Guardrails:
- online latency p99 < 180ms
- error rate скоринга заявок < 0.2%
- fairness disparity по age_group и region <= 0.08
Разделение трафика: 50% champion / 50% challenger по hashed applicant_id
Правила решения:
- продвигать только если default rate улучшается минимум на 1.5% относительно и p-value < 0.05
- auto-rollback если latency или fairness guardrail нарушается 30 минут подряд
Результат: дизайн эксперимента, расчёт sample size, ежедневный план мониторинга и шаблон финального решения о promotion
```

---

## Example 2 — Search ranking experiment with segment safety

**EN:**
```
/champion-challenger

Champion model: search-ranker-bert-v8
Challenger model: search-ranker-bert-v9-distilled
Experiment duration: 7 days during normal traffic period (exclude Black Friday campaign week)
Primary metric: click-through rate on top-5 search results
Secondary metrics:
- add-to-cart rate from search sessions
- zero-result session rate
- median inference cost per 1k requests
Segments that must not regress: mobile web, long-tail queries, German locale
Rollback policy: if challenger harms any protected segment by > 2% relative CTR for 24h, revert all traffic to champion
Output: experiment assignment strategy, segment analysis requirements, and final report structure for registry and product stakeholders
```

**RU:**
```
/champion-challenger

Champion model: search-ranker-bert-v8
Challenger model: search-ranker-bert-v9-distilled
Длительность эксперимента: 7 дней в период обычного трафика (исключая неделю кампании Black Friday)
Основная метрика: click-through rate по top-5 результатам поиска
Вторичные метрики:
- add-to-cart rate из search sessions
- zero-result session rate
- median inference cost на 1k запросов
Сегменты, которые не должны деградировать: mobile web, long-tail queries, немецкая локаль
Политика отката: если challenger ухудшает любой защищённый сегмент более чем на 2% относительного CTR в течение 24ч, вернуть весь трафик champion'у
Результат: стратегия назначения эксперимента, требования к segment analysis и структура финального отчёта для registry и продуктовых стейкхолдеров
```
