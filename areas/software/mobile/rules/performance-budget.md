---
description: Startup, memory, frame rate, and list rendering limits for iOS, Android, and React Native apps.
paths:
  - "**/*.swift"
  - "**/*.kt"
  - "**/*.tsx"
  - "ios/**"
  - "android/**"
---

# Mobile performance budget

- Keep cold start under 3 s and time to interactive under 2 s on the slowest supported device.
- Limit background memory use to 100 MB.
- Keep the UI at 60 fps; fail a release check that measures below 30 fps on a supported device.
- Limit the React Native JavaScript bundle to 4 MB.
- Do not run long computations on the UI or JavaScript thread; move them to a worker or native module.
- Use `FlatList` or `FlashList` for lists of unknown length, never `ScrollView`.
- Resize images to their display size before load and use a caching image component.
- Enable the Hermes engine (`hermesEnabled`) on both platforms in React Native projects.
