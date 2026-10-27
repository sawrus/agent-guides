---
description: Offline behaviour and sync queue constraints for iOS, Android, and React Native apps.
paths:
  - "**/*.swift"
  - "**/*.kt"
  - "**/*.dart"
  - "ios/**"
  - "android/**"
---

# Offline first

- Update the UI before the network request returns, and roll back the change when the request fails.
- Show an offline state with a retry action on every screen that needs network data; never render a blank screen.
- Persist the outgoing action queue to disk (database or file), not only in memory.
- Run the queued requests when connectivity returns, including from a background task.
- Define one conflict resolution strategy per synced entity type and document it next to the sync code.
- Label cached data older than its freshness limit with the time of the last update.
