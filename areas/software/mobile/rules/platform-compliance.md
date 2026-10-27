---
description: App Store and Play Store requirements for permissions, SDK versions, and privacy declarations.
paths:
  - "ios/**/Info.plist"
  - "**/Info.plist"
  - "android/**/build.gradle*"
  - "**/AndroidManifest.xml"
---

# Platform compliance

- Add a usage description key in `Info.plist` for every capability the app uses (camera, location, microphone).
- Update the App Store privacy labels and the Play Console data safety form in the same change that collects a new data type.
- Use Apple in-app purchase (`StoreKit`) for digital goods in App Store builds.
- Set the minimum iOS version to 16 or later unless the project documents another value.
- Request Android dangerous permissions at the point of use, not at app launch.
- Keep `targetSdkVersion` within 1 year of the latest Android API level.
- Include 64-bit builds of every native library.
