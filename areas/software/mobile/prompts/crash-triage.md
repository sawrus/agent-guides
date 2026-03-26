---
workflow: crash-triage
---

# Prompt: `/crash-triage`

Use when: a production crash is reported via Crashlytics, Sentry, or user report.

---

## Example 1 — Crashlytics crash with symbolication

**EN:**
```
/crash-triage

Crash: NullPointerException in OrderDetailViewModel.loadOrder()
Platform: Android 13, Samsung Galaxy S23
Crash rate: 2.3% of sessions (affecting ~4 500 users)
Crashlytics issue ID: CR-2024-1234
First seen: 3 days ago (correlates with v2.1.0 release)
Stack trace: attached from Crashlytics (unsymbolicated)
Suspected: race condition — user navigating away before async load completes
```

**RU:**
```
/crash-triage

Крэш: NullPointerException в OrderDetailViewModel.loadOrder()
Платформа: Android 13, Samsung Galaxy S23
Частота крэшей: 2.3% сессий (~4 500 пользователей)
Crashlytics issue ID: CR-2024-1234
Первый раз замечен: 3 дня назад (совпадает с релизом v2.1.0)
Stack trace: приложен из Crashlytics (без символикации)
Предположение: race condition — пользователь уходит со страницы до завершения async загрузки
```

---

## Example 2 — iOS crash on specific device

**EN:**
```
/crash-triage

Crash: EXC_BAD_ACCESS in ImageCacheManager
Platform: iOS 17.2, iPhone 15 Pro only (not reproducible on older devices)
Crash rate: 8% on iPhone 15 Pro, 0% on other devices
Suspected: memory pressure on ProMotion display with high-res images
dSYM available: yes (uploaded to Xcode Organizer)
```

**RU:**
```
/crash-triage

Крэш: EXC_BAD_ACCESS в ImageCacheManager
Платформа: iOS 17.2, только iPhone 15 Pro (не воспроизводится на старых устройствах)
Частота крэшей: 8% на iPhone 15 Pro, 0% на других устройствах
Предположение: memory pressure на ProMotion дисплее с высококачественными изображениями
dSYM доступен: да (загружен в Xcode Organizer)
```
