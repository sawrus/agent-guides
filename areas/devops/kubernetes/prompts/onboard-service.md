---
workflow: onboard-service
---

# Prompt: `/onboard-service`

Use when: deploying a new application to Kubernetes with namespace, workload, and least-privilege access defined together.

---

## Example 1 — Internal backend service

**EN:**
```
/onboard-service

Service: notification-service / Team: platform-team / Env: production
Image: registry.internal/notification-service:v1.0.0 / Port: 8080
Health: /health/ready, /health/live
Resource profile: small (100m CPU / 128Mi memory requests)
Calls: smtp-relay.infra:25, redis.cache:6379
Called by: order-service (namespace: production)
External: no
Required: namespace, ServiceAccount, RBAC, NetworkPolicy, Helm chart, ArgoCD app, HPA (min 2 max 8), ServiceMonitor
```

**RU:**
```
/onboard-service

Сервис: notification-service / Команда: platform-team / Окружение: production
Image: registry.internal/notification-service:v1.0.0 / Порт: 8080
Health: /health/ready, /health/live
Профиль ресурсов: small (100m CPU / 128Mi memory requests)
Вызывает: smtp-relay.infra:25, redis.cache:6379
Вызывается: order-service (namespace: production)
Внешний доступ: нет
Требуется: namespace, ServiceAccount, RBAC, NetworkPolicy, Helm chart, ArgoCD app, HPA (min 2 max 8), ServiceMonitor
```

---

## Example 2 — Externally exposed service with TLS

**EN:**
```
/onboard-service

Service: api-gateway / Team: backend-team / Env: staging
Image: registry.internal/api-gateway:v0.9.0 / Port: 8080
External: yes — NGINX Ingress at api.staging.example.com, TLS via cert-manager (Let's Encrypt)
Resource profile: medium (250m CPU / 256Mi memory)
Auth: mTLS between internal services
PDB: minAvailable 1 (staging has >= 2 replicas)
```

**RU:**
```
/onboard-service

Сервис: api-gateway / Команда: backend-team / Окружение: staging
Image: registry.internal/api-gateway:v0.9.0 / Порт: 8080
Внешний доступ: да — NGINX Ingress на api.staging.example.com, TLS через cert-manager (Let's Encrypt)
Профиль ресурсов: medium (250m CPU / 256Mi memory)
Auth: mTLS между внутренними сервисами
PDB: minAvailable 1 (в staging минимум 2 реплики)
```

---

## Example 3 — Pre-compliance namespace audit

**EN:**
```
/onboard-service

Target: namespace production
Goal: identify overprivileged accounts before SOC 2 review
Checks:
  - ServiceAccounts with automountServiceAccountToken: true
  - Bindings referencing cluster-admin or wildcard verbs/resources
  - Orphaned ServiceAccounts (no workload)
  - SA with cross-namespace ClusterRoleBindings
  - CI/CD SA (github-actions-sa) permissions vs required minimum
Output: findings table (SA / bound role / verdict: OK|REDUCE|REMOVE) + fix manifests
```

**RU:**
```
/onboard-service

Цель: namespace production
Задача: выявить привилегированные аккаунты перед SOC 2 ревью
Проверки:
  - ServiceAccount с automountServiceAccountToken: true
  - Bindings ссылающиеся на cluster-admin или wildcard verbs/resources
  - Orphaned ServiceAccount (без workload)
  - SA с межnamespace ClusterRoleBinding
  - Права CI/CD SA (github-actions-sa) vs необходимый минимум
Результат: таблица находок (SA / роль / вердикт: OK|REDUCE|REMOVE) + fix манифесты
```
