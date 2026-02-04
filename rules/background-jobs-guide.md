---
trigger: model_decision
glob: background-jobs-guide
description: manage background tasks safely and reliably
---

# Background Jobs Rule

**Rules:**

- Use queues for async jobs (Celery, RQ, etc.).
- Ensure idempotency for retried jobs.
- Log errors and metrics for each task.
- Limit concurrency and handle exceptions explicitly.

**Violations:**

- Jobs are non-idempotent.
- Exceptions crash the worker.
- No logging/metrics for task execution.
