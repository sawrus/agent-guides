---
workflow: debug-workload
---

# Prompt: `/debug-workload`

Use when: a pod is not Running, a service is unreachable, or a deployment is stuck.

---

## Example 1 — CrashLoopBackOff diagnosis

**EN:**
```
/debug-workload

Service: payment-service
Namespace: production
Symptom: CrashLoopBackOff — pod restarts every 30s since v2.3.1 deploy at 14:22 UTC
Last known good version: v2.3.0
What to check: exit code from describe, previous logs, image digest diff, recent ConfigMap/Secret changes
Output: root cause + fix as Helm values change (not kubectl edit)
```

**RU:**
```
/debug-workload

Сервис: payment-service
Namespace: production
Симптом: CrashLoopBackOff — перезапуск каждые 30с с деплоя v2.3.1 в 14:22 UTC
Последняя рабочая версия: v2.3.0
Что проверить: код выхода через describe, логи --previous, diff image digest, изменения ConfigMap/Secret
Результат: корневая причина + исправление как Helm values (не kubectl edit)
```

---

## Example 2 — Service unreachable (empty endpoints)

**EN:**
```
/debug-workload

Service: order-service / Namespace: production
Symptom: HTTP 503 from Ingress; endpoints empty despite 3/3 pods Running
Investigate: pod labels vs Service selector, ReadinessProbe status, NetworkPolicy blocking kubelet health check
Port mapping: container 8080, service 80 → targetPort 8080
```

**RU:**
```
/debug-workload

Сервис: order-service / Namespace: production
Симптом: HTTP 503 от Ingress; endpoints пустые хотя 3/3 поды Running
Расследовать: labels подов vs selector сервиса, статус ReadinessProbe, NetworkPolicy блокирующий kubelet health check
Маппинг портов: container 8080, service 80 → targetPort 8080
```

---

## Example 3 — OOMKilled + right-size

**EN:**
```
/debug-workload

Service: ml-inference-worker / Namespace: ml-prod
Symptom: OOMKilled (exit 137), 12 restarts in last hour; current limit: 512Mi
Task:
  1. Confirm OOMKill via describe + exit code
  2. Query Prometheus p99 memory over 7 days
  3. Calculate new limit = p99 × 1.3
  4. Update Helm values; do NOT patch production directly
  5. Check VPA recommendation if available
```

**RU:**
```
/debug-workload

Сервис: ml-inference-worker / Namespace: ml-prod
Симптом: OOMKilled (exit 137), 12 перезапусков за час; текущий лимит: 512Mi
Задача:
  1. Подтвердить OOMKill через describe + код выхода
  2. Запросить Prometheus p99 памяти за 7 дней
  3. Рассчитать новый лимит = p99 × 1.3
  4. Обновить Helm values; НЕ патчить production напрямую
  5. Проверить рекомендацию VPA если доступен
```
