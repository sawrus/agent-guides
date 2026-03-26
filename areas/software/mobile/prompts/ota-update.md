---
workflow: ota-update
---

# Prompt: `/ota-update`

Use when: deploying a JavaScript bundle update via Expo EAS Update or CodePush without a store review cycle.

---

## Example 1 — Critical bug fix OTA

**EN:**
```
/ota-update

Tool: Expo EAS Update
Change: hotfix - payment confirmation screen showed wrong total (display bug only, no data corruption)
Target versions: 3.1.x and 3.2.x (both affected)
Rollout: 100% immediately (critical display bug, low risk)
Validation: test on iOS 16+ and Android 12+ before push
Rollback plan: revert to previous update bundle if error rate increases
```

**RU:**
```
/ota-update

Инструмент: Expo EAS Update
Изменение: хотфикс - экран подтверждения платежа показывал неверную сумму (только визуальный баг, данные не повреждены)
Целевые версии: 3.1.x и 3.2.x (обе затронуты)
Выкатка: 100% сразу (критический визуальный баг, низкий риск)
Валидация: протестировать на iOS 16+ и Android 12+ перед публикацией
План отката: откатить к предыдущему bundle если вырастет error rate
```

---

## Example 2 — Staged OTA for a settings-screen regression

**EN:**
```
/ota-update

Tool: CodePush
Change: JS-only fix for settings screen where toggling push notifications resets language preference
Target audience: app versions 3.3.0 and 3.3.1, production channel only
Rollout plan:
- 5% for 1 hour
- 50% after crash-free rate and JS error rate stay stable
- 100% by the next morning if adoption is healthy
Checks:
- confirm no native permissions or config plugins changed
- monitor JS error fingerprints in Sentry during rollout
- prepare CodePush rollback command before the 5% stage starts
Output: rollout checklist, validation evidence, and adoption monitoring plan for 48h
```

**RU:**
```
/ota-update

Инструмент: CodePush
Изменение: JS-only исправление экрана настроек, где переключение push notifications сбрасывает language preference
Целевая аудитория: версии приложения 3.3.0 и 3.3.1, только production channel
План выката:
- 5% на 1 час
- 50% после того как crash-free rate и JS error rate останутся стабильными
- 100% к следующему утру, если adoption проходит нормально
Проверки:
- подтвердить, что native permissions и config plugins не менялись
- мониторить JS error fingerprints в Sentry во время rollout
- подготовить команду CodePush rollback до старта этапа 5%
Результат: rollout checklist, validation evidence и план мониторинга adoption на 48ч
```
