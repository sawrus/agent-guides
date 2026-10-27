---
description: Personal data handling in pipelines and warehouse models, covering hashing, minimization, and erasure.
paths:
  - "**/models/**"
  - "**/dags/**"
  - "**/pipelines/**"
---

# PII handling

- Store only a hashed or tokenized `user_id` in analytical tables; never store email, name, or phone columns there.
- Use SHA-256 with a secret salt, or tokens, for direct identifier columns.
- Keep only generalized quasi-identifier columns (birth year, ZIP prefix) in analytical models.
- Encrypt columns with health or financial data and limit read access with a role grant.
- Delete row-level behavioural data (clickstream, location) after 30 days; keep only aggregates.
- Apply a user deletion request to every table within 30 days.
- Document the reason for every new personal data field in the source schema file.
- Store EU resident data only in EU regions unless the project documents a legal transfer basis in its `docs/` page.
