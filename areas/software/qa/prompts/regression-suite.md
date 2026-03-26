---
workflow: regression-suite
---

# Prompt: `/regression-suite`

Use when: running full regression before a significant release or after a major code change.

---

## Example 1 — Release regression

**EN:**
```
/regression-suite

Environment: staging (release candidate v3.0.0)
Scope: full — all test categories
Release context: major version; includes DB schema migration for orders table
High-risk areas: order creation, payment processing, user authentication
Expected duration: ~45 min
Failure policy: any blocker in high-risk area → hold release
```

**RU:**
```
/regression-suite

Окружение: staging (release candidate v3.0.0)
Скоуп: полный — все категории тестов
Контекст релиза: мажорная версия; включает миграцию схемы для таблицы orders
Зоны высокого риска: создание заказов, обработка платежей, аутентификация
Ожидаемое время: ~45 мин
Политика отказов: любой blocker в зоне высокого риска → задержать релиз
```

---

## Example 2 — Targeted regression after change

**EN:**
```
/regression-suite

Environment: staging
Scope: targeted — auth module and all downstream tests
Reason: SSO provider upgrade to SAML 2.0 — auth flow changed
Tests to include: login, logout, token refresh, session expiry, SSO redirect
Skip: unrelated UI tests (save time)
```

**RU:**
```
/regression-suite

Окружение: staging
Скоуп: целевой — модуль auth и все зависимые тесты
Причина: обновление SSO провайдера до SAML 2.0 — изменён auth flow
Тесты для включения: login, logout, token refresh, session expiry, SSO redirect
Пропустить: несвязанные UI тесты (экономия времени)
```
