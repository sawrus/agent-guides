---
trigger: model_decision
glob: error-handling-guide
description: explicit exception management and retry policies
---

# Error Handling Rule

**Rules:**

- Catch specific exceptions only; never base Exception.
- Retry with backoff for transient failures.
- Use circuit breakers for external calls.
- Log errors with context; propagate critical exceptions.

**Violations:**

- Root Exception is caught.
- Retries missing for transient errors.
- Critical failures are silenced.
