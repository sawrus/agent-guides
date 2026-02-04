---
trigger: model_decision
glob: async-concurrency-guide
description: isolate async code, use tasks safely
---

# Async & Concurrency Rule

**Rules:**

- Isolate async/TaskGroup logic from sync code.
- Do not block event loop with heavy computation.
- Catch only expected exceptions in async tasks.
- Ensure idempotency for retried tasks.
- Implement logic to debug event loop delays.

**Violations:**

- Async tasks share mutable state.
- Root Exception is caught.
- Tasks are non-idempotent.
