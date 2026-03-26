---
workflow: release-prep
---

# Prompt: `/release-prep`

Use when: preparing a frontend release with coordinated quality, performance, and stakeholder sign-off.

---

## Example 1 — Planned release

**EN:**
```
/release-prep

Release: v2.8.0
Scope: 3 new features (dark mode, notification center, dashboard redesign)
Target version: 2.8.0
Success criteria:
- Lighthouse performance score >= 85 on key pages
- Zero new WCAG A violations
- All regression tests pass
- Bundle size within budget (< 300KB gzipped main)
Known risk: notification center uses WebSocket - first time in the app
Release notes audience: end users (non-technical)
```

**RU:**
```
/release-prep

Релиз: v2.8.0
Скоуп: 3 новые фичи (dark mode, центр уведомлений, редизайн dashboard)
Целевая версия: 2.8.0
Критерии успеха:
- Lighthouse performance score >= 85 на ключевых страницах
- Ноль новых WCAG A нарушений
- Все regression tests проходят
- Размер bundle в рамках бюджета (< 300KB gzipped main)
Известный риск: центр уведомлений использует WebSocket - первый раз в приложении
Аудитория release notes: конечные пользователи (нетехнические)
```

---

## Example 2 — Hotfix release with rollback pressure

**EN:**
```
/release-prep

Release: v2.8.1-hotfix
Scope: fix checkout address form regression introduced in v2.8.0
Observed impact: 18% of mobile Safari users cannot submit checkout after postal code autofill
Constraints:
- ship within 4 hours
- keep rollback path to v2.8.0 build artifact
- only changed routes /checkout and /order-confirmation require focused visual regression review
Checks still required:
- smoke test on staging with Safari + Chrome mobile emulation
- confirm no new bundle regression on checkout chunk
- verify analytics event checkout_submit still fires exactly once
Output: go/no-go recommendation, rollback trigger list, and customer-facing release note for support team
```

**RU:**
```
/release-prep

Релиз: v2.8.1-hotfix
Скоуп: исправление регрессии формы адреса на checkout, внесённой в v2.8.0
Наблюдаемое влияние: 18% пользователей mobile Safari не могут отправить checkout после автозаполнения postal code
Ограничения:
- выпустить за 4 часа
- сохранить путь отката к build artifact версии v2.8.0
- только изменённые маршруты /checkout и /order-confirmation требуют focused visual regression review
Проверки, которые всё равно обязательны:
- smoke test на staging с Safari + Chrome mobile emulation
- подтвердить отсутствие новой bundle-регрессии в checkout chunk
- проверить, что analytics event checkout_submit всё ещё срабатывает ровно один раз
Результат: рекомендация go/no-go, список rollback trigger'ов и customer-facing release note для команды поддержки
```
