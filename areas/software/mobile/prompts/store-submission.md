---
workflow: store-submission
---

# Prompt: `/store-submission`

Use when: submitting a build to App Store Connect or Google Play Console for review.

---

## Example 1 — Full store submission

**EN:**
```
/store-submission

Platform: iOS + Android
Build: v3.2.0 (build 145) - already uploaded to App Store Connect + Play Console
New features to describe: dark mode, notification center
New permissions: push notifications (iOS - already in Info.plist)
Privacy policy: https://myapp.com/privacy (no changes)
Target regions: worldwide
Review notes for Apple: test account credentials in submission (email: review@myapp.com / Pass123!)
Screenshots: updated for iPhone 15 Pro, iPad, Pixel 8 (attached to submission)
```

**RU:**
```
/store-submission

Платформа: iOS + Android
Сборка: v3.2.0 (build 145) - уже загружена в App Store Connect + Play Console
Новые функции для описания: тёмная тема, центр уведомлений
Новые разрешения: push-уведомления (iOS - уже в Info.plist)
Политика конфиденциальности: https://myapp.com/privacy (изменений нет)
Целевые регионы: весь мир
Заметки для ревью Apple: учётные данные тестового аккаунта в заявке (email: review@myapp.com / Pass123!)
Скриншоты: обновлены для iPhone 15 Pro, iPad, Pixel 8 (приложены к заявке)
```

---

## Example 2 — Incremental Android rollout after a sensitive permissions change

**EN:**
```
/store-submission

Platform: Android
Build: v3.3.0 (versionCode 211)
Track: closed testing -> production 20% rollout
Change summary:
- added background location usage for courier tracking
- updated onboarding copy and in-app disclosures
Compliance requirements:
- Play Console data safety form must reflect continuous location collection
- screenshots updated for courier mode and permission education screen
- support team needs rollout notes and rejection fallback plan
Post-release monitoring: crash-free rate >= 99.5% for 48h and no spike in 1-star reviews mentioning permissions
Output: submission checklist, metadata package, and monitoring plan for staged production rollout
```

**RU:**
```
/store-submission

Платформа: Android
Сборка: v3.3.0 (versionCode 211)
Трек: closed testing -> production rollout 20%
Сводка изменений:
- добавлено использование background location для courier tracking
- обновлены onboarding copy и in-app disclosures
Требования compliance:
- форма Play Console data safety должна отражать постоянный сбор location
- скриншоты обновлены для courier mode и экрана объяснения permission
- команде поддержки нужны rollout notes и план действий на случай rejection
Пострелизный мониторинг: crash-free rate >= 99.5% в течение 48ч и отсутствие всплеска 1-star review с упоминанием permissions
Результат: submission checklist, пакет metadata и план мониторинга для staged production rollout
```
