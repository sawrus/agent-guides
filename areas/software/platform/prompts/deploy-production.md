---
workflow: deploy-production
---

# Prompt: `/deploy-production`

Use when: executing a production deployment with canary rollout, progressive traffic shifting, and automated rollback gates.

---

## Example 1 — Canary deploy with progressive rollout

**EN:**
```
/deploy-production

Service: order-service
Version: v2.5.0 → v2.6.0
Deployment strategy: canary → progressive (10% → 50% → 100%)
Infrastructure: Kubernetes (EKS), ArgoCD for GitOps
Image: ghcr.io/myorg/order-service:2.6.0 (digest: sha256:abc...)
Pre-flight checks:
  - All integration tests passing on staging
  - DB migration alembic upgrade head — already applied (non-breaking)
  - Dependent services: payment-service v1.9+ (compatible), notification-service (no change)
Rollback trigger: error rate > 1% OR p99 > 2s sustained for 5 min at any canary stage
Monitoring: Datadog dashboard "order-service canary" — open during deploy
On-call engineer: @devops-lead (PagerDuty)
```

**RU:**
```
/deploy-production

Сервис: order-service
Версия: v2.5.0 → v2.6.0
Стратегия деплоя: canary → progressive (10% → 50% → 100%)
Инфраструктура: Kubernetes (EKS), ArgoCD для GitOps
Образ: ghcr.io/myorg/order-service:2.6.0 (digest: sha256:abc...)
Pre-flight проверки:
  - Все integration тесты проходят на staging
  - Миграция БД alembic upgrade head — уже применена (non-breaking)
  - Зависимые сервисы: payment-service v1.9+ (совместимо), notification-service (без изменений)
Триггер отката: error rate > 1% ИЛИ p99 > 2s в течение 5 мин на любом этапе canary
Мониторинг: Datadog dashboard "order-service canary" — открыт во время деплоя
Дежурный инженер: @devops-lead (PagerDuty)
```

---

## Example 2 — Hotfix emergency deploy

**EN:**
```
/deploy-production

Service: payment-service
Version: v3.1.1 (hotfix) — patches critical payment failure bug (INC-2024-142)
Deployment strategy: full rollout immediately (skip canary — confirmed fix, low risk change)
Justification: 3-line fix to null check; confirmed root cause; no schema changes
Approvals obtained: CTO + Lead Engineer (Slack thread attached)
Pre-deploy: smoke test against staging with fix deployed — PASSED
Post-deploy validation:
  - Monitor error rate on /api/v1/payments for 15 minutes
  - Confirm incident INC-2024-142 resolved (check Sentry error count drops to 0)
Rollback: revert to v3.1.0 image (available in registry) if validation fails
```

**RU:**
```
/deploy-production

Сервис: payment-service
Версия: v3.1.1 (hotfix) — исправляет критический баг сбоя платежей (INC-2024-142)
Стратегия деплоя: полный rollout немедленно (пропустить canary — подтверждённое исправление, низкий риск)
Обоснование: исправление 3 строк для null check; корневая причина подтверждена; нет изменений схемы
Полученные одобрения: CTO + Lead Engineer (Slack тред приложен)
Pre-deploy: smoke test на staging с применённым исправлением — ПРОЙДЕН
Валидация после деплоя:
  - Мониторить error rate на /api/v1/payments 15 минут
  - Подтвердить разрешение инцидента INC-2024-142 (проверить снижение счётчика ошибок Sentry до 0)
Откат: вернуться к образу v3.1.0 (доступен в registry) если валидация не пройдёт
```

---

## Example 3 — Multi-service coordinated deploy

**EN:**
```
/deploy-production

Services: [user-service v2.1.0, auth-service v1.8.0] — must deploy together (breaking API contract change)
Coordination: auth-service first (backward-compatible for 30 min window), then user-service
Downtime window: none — both services must be live simultaneously during transition
Validation: run auth integration test suite against prod after each service deploy
Rollback order: user-service first, then auth-service (reverse deploy order)
```

**RU:**
```
/deploy-production

Сервисы: [user-service v2.1.0, auth-service v1.8.0] — должны деплоиться вместе (breaking изменение API контракта)
Координация: сначала auth-service (обратно-совместимый в течение 30-минутного окна), затем user-service
Окно простоя: нет — оба сервиса должны работать одновременно в период перехода
Валидация: запустить набор auth integration тестов против прода после деплоя каждого сервиса
Порядок отката: сначала user-service, затем auth-service (обратный порядок деплоя)
```
