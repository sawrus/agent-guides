---
workflow: release-build
---

# Prompt: `/release-build`

Use when: creating a production-ready build for app store submission or internal distribution.

---

## Example 1 — App Store release build

**EN:**
```
/release-build

Platform: iOS + Android
Version: 3.2.0 (build 145)
Release type: production App Store / Google Play
Signing: iOS — Distribution certificate + App Store provisioning profile; Android — release keystore (CI secrets)
Environment: prod API (https://api.myapp.com)
Changes since last build: notification center, dark mode, performance fixes
Required: changelogs for both stores (EN + RU)
CI: GitHub Actions (fastlane lanes: ios_release, android_release)
```

**RU:**
```
/release-build

Платформа: iOS + Android
Версия: 3.2.0 (сборка 145)
Тип релиза: production App Store / Google Play
Подпись: iOS — Distribution certificate + App Store provisioning profile; Android — release keystore (CI secrets)
Окружение: prod API (https://api.myapp.com)
Изменения с прошлой сборки: центр уведомлений, тёмная тема, исправления производительности
Необходимо: changelogs для обеих магазинов (EN + RU)
CI: GitHub Actions (fastlane lanes: ios_release, android_release)
```

---

## Example 2 — Internal/QA distribution build

**EN:**
```
/release-build

Platform: Android only
Version: 3.2.0-rc.2 (build 143)
Release type: internal testing (Firebase App Distribution)
Environment: staging API
Testers: QA team + product managers (distribution group: "qa-team")
No store screenshots or release notes needed
```

**RU:**
```
/release-build

Платформа: только Android
Версия: 3.2.0-rc.2 (сборка 143)
Тип релиза: внутреннее тестирование (Firebase App Distribution)
Окружение: staging API
Тестировщики: QA команда + продакт менеджеры (группа: "qa-team")
Скриншоты для магазина и release notes не нужны
```
