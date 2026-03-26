---
workflow: secret-rotation
---

# Prompt: `/secret-rotation`

Use when: rotating credentials, API keys, or certificates without service downtime — using the dual-read window pattern.

---

## Example 1 — Database password rotation

**EN:**
```
/secret-rotation

Secret type: PostgreSQL superuser password (prod)
Reason: scheduled quarterly rotation (compliance requirement)
Services consuming this secret: order-service, payment-service, analytics-service
Secret manager: AWS Secrets Manager
Current secret name: prod/db/postgres-password
Rotation strategy: dual-read window
  Phase 1: create new password, store as prod/db/postgres-password-new
  Phase 2: deploy all services with dual-read (try new → fall back to old)
  Phase 3: verify all services healthy with new password
  Phase 4: revoke old password, rename new → canonical
Rollback plan: revert all services to old secret if error rate > 0.1% in Phase 3
Zero-downtime requirement: yes — prod traffic must not be interrupted
```

**RU:**
```
/secret-rotation

Тип секрета: пароль суперпользователя PostgreSQL (prod)
Причина: плановая квартальная ротация (требование compliance)
Сервисы использующие этот секрет: order-service, payment-service, analytics-service
Secret manager: AWS Secrets Manager
Текущее имя секрета: prod/db/postgres-password
Стратегия ротации: dual-read window
  Фаза 1: создать новый пароль, сохранить как prod/db/postgres-password-new
  Фаза 2: задеплоить все сервисы с dual-read (пробовать новый → откат к старому)
  Фаза 3: убедиться что все сервисы здоровы с новым паролем
  Фаза 4: отозвать старый пароль, переименовать новый → канонический
План отката: откатить все сервисы к старому секрету если error rate > 0.1% в Фазе 3
Требование zero-downtime: да — прод трафик не должен прерываться
```

---

## Example 2 — Third-party API key rotation (after suspected leak)

**EN:**
```
/secret-rotation

Secret type: Stripe secret API key (sk_live_...)
Reason: URGENT — key found in git history (commit abc1234, merged 6 days ago)
Risk: key may be compromised; unknown if exploited
Immediate actions needed:
  1. Generate new Stripe key NOW via Stripe dashboard
  2. Deploy new key to all environments (prod, staging) within 30 minutes
  3. Revoke old key in Stripe dashboard
  4. Audit Stripe dashboard for unexpected API calls in last 6 days
  5. Add git-secrets / trufflehog pre-commit hook to prevent recurrence
Services affected: payment-service, subscription-service
Secret manager: HashiCorp Vault
```

**RU:**
```
/secret-rotation

Тип секрета: Stripe secret API key (sk_live_...)
Причина: СРОЧНО — ключ найден в git истории (коммит abc1234, слит 6 дней назад)
Риск: ключ может быть скомпрометирован; неизвестно был ли использован
Немедленные действия:
  1. Сгенерировать новый Stripe ключ СЕЙЧАС через Stripe dashboard
  2. Задеплоить новый ключ во все окружения (prod, staging) в течение 30 минут
  3. Отозвать старый ключ в Stripe dashboard
  4. Проверить Stripe dashboard на неожиданные API вызовы за последние 6 дней
  5. Добавить git-secrets / trufflehog pre-commit hook для предотвращения рецидива
Затронутые сервисы: payment-service, subscription-service
Secret manager: HashiCorp Vault
```

---

## Example 3 — TLS certificate renewal

**EN:**
```
/secret-rotation

Secret type: TLS certificate for api.myapp.com (Let's Encrypt)
Reason: certificate expires in 14 days (automated renewal failed)
Current location: Kubernetes Secret tls-api-cert in namespace prod
Renewal tool: cert-manager (already installed, renewal should be automatic)
Diagnose: check cert-manager logs for renewal failure reason
After renewal: verify new cert loaded by nginx ingress without pod restart
Alert: set up monitoring alert if cert expiry < 30 days
```

**RU:**
```
/secret-rotation

Тип секрета: TLS сертификат для api.myapp.com (Let's Encrypt)
Причина: сертификат истекает через 14 дней (автоматическое обновление не сработало)
Текущее расположение: Kubernetes Secret tls-api-cert в namespace prod
Инструмент обновления: cert-manager (уже установлен, обновление должно быть автоматическим)
Диагностика: проверить логи cert-manager на причину сбоя обновления
После обновления: убедиться что новый сертификат загружен nginx ingress без перезапуска подов
Оповещение: настроить monitoring alert если истечение cert < 30 дней
```
