---
workflow: policy-onboard
---

# Prompt: `/policy-onboard`

Use when: adding OPA/Kyverno admission policies to a cluster or namespace.

---

## Example 1 — Full admission policy baseline for new cluster

**EN:**
```
/policy-onboard

Cluster: prod-cluster-eu
Policy engine: OPA/Gatekeeper (already installed)
Scope: all namespaces labelled environment=production or environment=staging
Policies to deploy (enforcement: deny for prod, warn for staging):
  - require-non-root (runAsNonRoot: true, UID != 0)
  - disallow-privileged-containers
  - require-resource-limits (CPU + memory both required)
  - require-image-digest (no :latest or mutable tags)
  - disallow-host-namespaces (no hostNetwork/hostPID/hostIPC)
  - require-labels: app, team, environment on all Deployments
Test each policy with: passing manifest + failing manifest before deploying
```

**RU:**
```
/policy-onboard

Кластер: prod-cluster-eu
Policy engine: OPA/Gatekeeper (уже установлен)
Скоуп: все namespaces с лейблом environment=production или environment=staging
Политики для деплоя (enforcement: deny для prod, warn для staging):
  - require-non-root (runAsNonRoot: true, UID != 0)
  - disallow-privileged-containers
  - require-resource-limits (CPU + memory оба обязательны)
  - require-image-digest (без :latest и mutable тегов)
  - disallow-host-namespaces (без hostNetwork/hostPID/hostIPC)
  - require-labels: app, team, environment на всех Deployment
Протестировать каждую политику с: passing манифест + failing манифест перед деплоем
```

---

## Example 2 — Fix policy-blocked deployment

**EN:**
```
/policy-onboard

Problem: Deployment of order-service v3.0.0 blocked by admission webhook
Error: "admission webhook gatekeeper denied: Container 'app' must set runAsNonRoot: true"
Current Dockerfile: no USER instruction; runs as root
Fix needed:
  1. Add USER 1000:1000 to Dockerfile
  2. Add securityContext.runAsNonRoot: true + runAsUser: 1000 to Helm values
  3. Verify readOnlyRootFilesystem: true won't break app (check for writes to / )
  4. Rebuild image + re-deploy
  5. Confirm no other policy violations in the same deployment
```

**RU:**
```
/policy-onboard

Проблема: деплой order-service v3.0.0 заблокирован admission webhook
Ошибка: "admission webhook gatekeeper denied: Container 'app' must set runAsNonRoot: true"
Текущий Dockerfile: нет инструкции USER; запускается от root
Необходимое исправление:
  1. Добавить USER 1000:1000 в Dockerfile
  2. Добавить securityContext.runAsNonRoot: true + runAsUser: 1000 в Helm values
  3. Убедиться что readOnlyRootFilesystem: true не сломает приложение (проверить записи в /)
  4. Пересобрать образ + повторить деплой
  5. Подтвердить отсутствие других нарушений политик в том же deployment
```
