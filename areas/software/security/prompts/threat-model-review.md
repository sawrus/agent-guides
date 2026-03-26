---
workflow: threat-model-review
---

# Prompt: `/threat-model-review`

Use when: reviewing an existing or new system design for security threats using STRIDE methodology before implementation or as part of an architecture review.

---

## Example 1 — New feature threat model

**EN:**
```
/threat-model-review

Feature: "OAuth2 social login (Google + GitHub)"
Stage: pre-implementation design review
System context:
  - Current auth: username/password with JWT (RS256)
  - Adding: OAuth2 authorization code flow
  - New components: OAuth callback endpoint, state parameter store (Redis), token exchange
  - User data stored: OAuth provider user ID, email, profile picture URL
Threat focus: token interception, CSRF via state param, account takeover via email collision
Assets to protect: user session, OAuth tokens, account linkage integrity
Output: STRIDE threat table + prioritised mitigations + go/no-go recommendation
```

**RU:**
```
/threat-model-review

Фича: "OAuth2 социальный вход (Google + GitHub)"
Этап: ревью дизайна до реализации
Системный контекст:
  - Текущая auth: username/password с JWT (RS256)
  - Добавляем: OAuth2 authorization code flow
  - Новые компоненты: OAuth callback endpoint, хранилище state параметра (Redis), обмен токенов
  - Хранимые данные пользователя: OAuth provider user ID, email, URL фото профиля
Фокус угроз: перехват токена, CSRF через state параметр, захват аккаунта через коллизию email
Защищаемые активы: пользовательская сессия, OAuth токены, целостность привязки аккаунта
Результат: таблица угроз STRIDE + приоритизированные меры защиты + рекомендация go/no-go
```

---

## Example 2 — Architecture-level review

**EN:**
```
/threat-model-review

System: payment processing service (PCI-DSS scope)
Review type: full architecture threat model (annual review)
Architecture:
  - Public API gateway → payment-service (internal) → Stripe API
  - Card data: never stored locally; tokenised via Stripe.js on client
  - Sensitive fields: card_last4, billing_address stored in payments table
  - Internal comms: mTLS between services
  - Admin access: VPN + MFA required
Compliance: PCI-DSS SAQ-A (card data handled by Stripe only)
Output: DFD diagram description + STRIDE analysis per trust boundary + compliance gap list
```

**RU:**
```
/threat-model-review

Система: сервис обработки платежей (зона PCI-DSS)
Тип ревью: полная threat model архитектуры (ежегодное ревью)
Архитектура:
  - Публичный API gateway → payment-service (внутренний) → Stripe API
  - Данные карт: никогда не хранятся локально; токенизируются через Stripe.js на клиенте
  - Чувствительные поля: card_last4, billing_address хранятся в таблице payments
  - Внутренние коммуникации: mTLS между сервисами
  - Доступ администратора: VPN + MFA обязательны
Соответствие: PCI-DSS SAQ-A (данные карт обрабатываются только Stripe)
Результат: описание DFD диаграммы + STRIDE анализ на каждой границе доверия + список несоответствий
```

---

## Example 3 — Quick / Single endpoint review

**EN:**
```
/threat-model-review

Scope: single endpoint — POST /admin/users/{id}/impersonate
Context: allows support team to log in as any user for debugging
Concerns: privilege escalation, audit trail completeness, session isolation
Must verify: impersonation sessions cannot perform irreversible actions (payments, deletions)
Output: threat list + required controls (audit log, scope restriction, TTL)
```

**RU:**
```
/threat-model-review

Скоуп: один эндпоинт — POST /admin/users/{id}/impersonate
Контекст: позволяет команде поддержки входить от имени любого пользователя для отладки
Опасения: эскалация привилегий, полнота audit trail, изоляция сессий
Обязательно проверить: сессии имперсонации не могут выполнять необратимые действия (платежи, удаления)
Результат: список угроз + необходимые меры (audit log, ограничение скоупа, TTL)
```
