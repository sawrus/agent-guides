---
workflow: model-incident
---

# Prompt: `/model-incident`

Use when: responding to model degradation, drift, bias, or endpoint outages that require rollback, diagnosis, and scoped remediation.

---

## Example 1 — Prediction drift after feature pipeline change

**EN:**
```
/model-incident

Model name: churn-predictor-v9
Incident type: drift
Symptoms:
- PSI on feature monthly_sessions = 0.34 (baseline alert threshold 0.2)
- probability distribution shifted heavily upward after 2026-03-20 09:00 UTC
- no serving error spike, but retention team reports doubled intervention volume
Recent changes: feature store job for monthly_sessions moved from daily batch to hourly incremental pipeline
Immediate need:
- decide whether to tolerate degraded predictions or rollback to previous champion
- scope the affected prediction window
- identify whether feature semantics changed or only data freshness changed
Output: severity classification, rollback recommendation, affected window, and remediation path
```

**RU:**
```
/model-incident

Model name: churn-predictor-v9
Тип инцидента: drift
Симптомы:
- PSI по признаку monthly_sessions = 0.34 (порог алерта baseline = 0.2)
- распределение вероятностей сильно сместилось вверх после 2026-03-20 09:00 UTC
- всплеска serving error нет, но retention team сообщает о двукратном росте intervention volume
Недавние изменения: job feature store для monthly_sessions переведён с daily batch на hourly incremental pipeline
Нужно немедленно:
- решить, терпим ли деградированные предсказания или откатываемся к предыдущему champion
- определить окно затронутых предсказаний
- понять, изменилась ли семантика признака или только data freshness
Результат: классификация severity, рекомендация по rollback, affected window и путь remediation
```

---

## Example 2 — Inference outage after container update

**EN:**
```
/model-incident

Model name: recommendations-transformer-v4
Incident type: outage
Symptoms:
- endpoint 5xx rate = 18% for 12 minutes
- pod logs show "CUDA out of memory" after new serving image deploy
- HPA scaled from 4 to 8 replicas, but latency still above 2.5s and readiness probes flap
Current impact: homepage recommendation widgets empty for 30% of sessions
Required response:
- stabilize service within 5 minutes, including rollback if needed
- determine whether the issue is model artifact size, batch size config, or infrastructure sizing
- notify downstream product analytics about affected prediction interval
Output: immediate response plan, rollback or mitigation action, and post-incident prevention changes
```

**RU:**
```
/model-incident

Model name: recommendations-transformer-v4
Тип инцидента: outage
Симптомы:
- 5xx rate endpoint'а = 18% в течение 12 минут
- логи pod'ов показывают "CUDA out of memory" после деплоя нового serving image
- HPA масштабировался с 4 до 8 реплик, но latency всё ещё выше 2.5s и readiness probes флапают
Текущее влияние: homepage widgets с рекомендациями пустые у 30% сессий
Требуемый ответ:
- стабилизировать сервис в течение 5 минут, включая rollback при необходимости
- определить, связана ли проблема с размером model artifact, batch size config или sizing инфраструктуры
- уведомить downstream product analytics о затронутом интервале предсказаний
Результат: план немедленного реагирования, rollback или mitigation action и изменения для предотвращения повторения
```
