---
workflow: device-testing
---

# Prompt: `/device-testing`

Use when: executing a structured test run across a device matrix before a release.

---

## Example 1 — Pre-release device matrix

**EN:**
```
/device-testing

Release: v3.2.0 (release candidate)
Platform: iOS + Android
Test matrix:
  iOS:     iPhone 15 Pro (iOS 17), iPhone 12 (iOS 16), iPad Air (iPadOS 16)
  Android: Pixel 8 (Android 14), Samsung Galaxy S21 (Android 13), OnePlus 9 (Android 12)
Test tool: AWS Device Farm (Detox E2E suite)
Critical flows: login, checkout, notifications, dark mode
Accept criteria: zero crashes, all critical flows pass on all devices
Blocking for release: any P1 crash on a supported device
```

**RU:**
```
/device-testing

Релиз: v3.2.0 (release candidate)
Платформа: iOS + Android
Матрица устройств:
  iOS:     iPhone 15 Pro (iOS 17), iPhone 12 (iOS 16), iPad Air (iPadOS 16)
  Android: Pixel 8 (Android 14), Samsung Galaxy S21 (Android 13), OnePlus 9 (Android 12)
Инструмент: AWS Device Farm (Detox E2E suite)
Критические потоки: вход, оформление заказа, уведомления, тёмная тема
Критерии приёмки: ноль крэшей, все критические потоки проходят на всех устройствах
Блокирует релиз: любой P1 крэш на поддерживаемом устройстве
```

---

## Example 2 — Post-fix focused matrix for a native permissions bug

**EN:**
```
/device-testing

Release: v3.2.1-rc1
Platform: Android only
Reason: camera permission flow was fixed after crashes on Samsung devices
Focused matrix:
  Android 14: Pixel 8, Galaxy S23
  Android 13: Galaxy S21, Xiaomi 12
  Android 12: OnePlus 9, Motorola Edge 30
Critical scenarios:
- first launch permission prompt
- deny -> re-open scanner flow
- grant permission from system settings and resume app
- background/foreground transition while camera preview is active
Accept criteria: zero crashes, no frozen preview, and permission state remains correct after process recreation
```

**RU:**
```
/device-testing

Релиз: v3.2.1-rc1
Платформа: только Android
Причина: исправлен flow camera permission после крэшей на устройствах Samsung
Фокусная матрица:
  Android 14: Pixel 8, Galaxy S23
  Android 13: Galaxy S21, Xiaomi 12
  Android 12: OnePlus 9, Motorola Edge 30
Критические сценарии:
- первый запуск permission prompt
- deny -> повторное открытие scanner flow
- выдача разрешения из system settings и возврат в приложение
- background/foreground transition при активном camera preview
Критерии приёмки: ноль крэшей, отсутствие зависшего preview и корректное сохранение permission state после process recreation
```
