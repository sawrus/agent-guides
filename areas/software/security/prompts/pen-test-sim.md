---
workflow: pen-test-sim
---

# Prompt: `/pen-test-sim`

Use when: simulating a penetration test on a staging environment to find exploitable vulnerabilities before they reach production.

---

## Example 1 — Full web application pen test

**EN:**
```
/pen-test-sim

Target: https://staging.myapp.com (isolated staging — not production)
Scope: web application only; infrastructure out of scope
Authorization: confirmed — written sign-off from CTO (attached)
Application type: SPA (React) + REST API (FastAPI) + PostgreSQL
Auth mechanism: JWT (RS256) in Authorization header + refresh token in HttpOnly cookie
Test areas (OWASP Top 10 focus):
  - A01 Broken Access Control: IDOR on /api/orders/{id}, horizontal privilege escalation
  - A02 Cryptographic Failures: JWT algorithm confusion (RS256→HS256), weak token entropy
  - A03 Injection: SQL injection in search/filter params, NoSQL injection if applicable
  - A07 Identity/Auth Failures: brute force, credential stuffing, session fixation
  - A09 Logging Failures: verify audit events present for sensitive actions
Test accounts: admin@test.myapp.com / viewer@test.myapp.com (credentials in vault)
Output: pentest-report.md — finding per OWASP category, CVSS score, PoC, remediation
```

**RU:**
```
/pen-test-sim

Цель: https://staging.myapp.com (изолированный staging — не production)
Скоуп: только веб-приложение; инфраструктура вне скоупа
Авторизация: подтверждена — письменное согласие от CTO (приложено)
Тип приложения: SPA (React) + REST API (FastAPI) + PostgreSQL
Механизм auth: JWT (RS256) в Authorization header + refresh token в HttpOnly cookie
Области тестирования (фокус OWASP Top 10):
  - A01 Broken Access Control: IDOR на /api/orders/{id}, горизонтальная эскалация привилегий
  - A02 Cryptographic Failures: JWT algorithm confusion (RS256→HS256), слабая энтропия токена
  - A03 Injection: SQL injection в параметрах поиска/фильтрации, NoSQL injection если применимо
  - A07 Identity/Auth Failures: brute force, credential stuffing, session fixation
  - A09 Logging Failures: проверить наличие audit событий для чувствительных действий
Тестовые аккаунты: admin@test.myapp.com / viewer@test.myapp.com (credentials в vault)
Результат: pentest-report.md — находка по категории OWASP, CVSS оценка, PoC, устранение
```

---

## Example 2 — API-only targeted test

**EN:**
```
/pen-test-sim

Target: staging API — https://api-staging.myapp.com/api/v1
Scope: REST API endpoints only (no frontend, no infrastructure)
Focus: authentication bypass and authorisation boundary violations
Specific concern: new multi-tenant feature — verify tenant A cannot access tenant B data
Test vectors:
  - JWT tampering: modify tenant_id claim, try none algorithm
  - Forced browsing: enumerate /api/v1/tenants/{id}/... with ids 1–1000
  - Mass assignment: send undocumented fields in PATCH requests
  - Rate limiting: confirm 429 on /api/v1/auth/token after 10 failed attempts
Tools: Burp Suite CE, custom Python scripts
Output: findings per endpoint with HTTP request/response evidence
```

**RU:**
```
/pen-test-sim

Цель: staging API — https://api-staging.myapp.com/api/v1
Скоуп: только REST API эндпоинты (без фронтенда, без инфраструктуры)
Фокус: обход аутентификации и нарушения границ авторизации
Конкретная озабоченность: новая multi-tenant фича — убедиться что tenant A не может получить данные tenant B
Тестовые векторы:
  - JWT tampering: изменить claim tenant_id, попробовать алгоритм none
  - Forced browsing: перечислить /api/v1/tenants/{id}/... с id 1–1000
  - Mass assignment: отправить недокументированные поля в PATCH запросах
  - Rate limiting: убедиться в 429 на /api/v1/auth/token после 10 неудачных попыток
Инструменты: Burp Suite CE, кастомные Python скрипты
Результат: находки по эндпоинту с доказательствами HTTP запрос/ответ
```

---

## Example 3 — Quick / Auth flow check

**EN:**
```
/pen-test-sim

Scope: authentication flow only — login, registration, password reset
Target: staging environment
Check: password reset token entropy (should be ≥ 128 bits); token expiry enforced;
reset link single-use; account enumeration via timing attack on /auth/login
Output: pass/fail per check with evidence; critical findings block release
```

**RU:**
```
/pen-test-sim

Скоуп: только поток аутентификации — вход, регистрация, сброс пароля
Цель: staging окружение
Проверить: энтропия токена сброса пароля (должна быть ≥ 128 бит); истечение токена соблюдается;
ссылка для сброса одноразовая; перечисление аккаунтов через timing attack на /auth/login
Результат: pass/fail по каждой проверке с доказательствами; критические находки блокируют релиз
```
