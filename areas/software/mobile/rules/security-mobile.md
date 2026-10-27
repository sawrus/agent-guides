---
description: On-device storage, logging, screenshots, and deep link security for mobile apps.
paths:
  - "**/*.swift"
  - "**/*.kt"
  - "**/*.tsx"
  - "ios/**"
  - "android/**"
---

# Mobile security

- Store tokens, passwords, and personal data only in the Keychain or Android Keystore, never in `AsyncStorage` or `SharedPreferences`.
- Enable certificate pinning in apps that handle payment or health data.
- Do not log tokens or personal data; disable debug log levels in release builds.
- Set `FLAG_SECURE` on Android and hide content on iOS for payment and authentication screens.
- Validate the scheme, host, and path of every deep link before the app reads its query parameters.
