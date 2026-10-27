---
description: Documentation, ownership, classification, and freshness requirements for warehouse tables and dbt models.
paths:
  - "**/models/**/*.yml"
  - "**/models/**/*.sql"
  - "dbt_project.yml"
---

# Data governance

- Add a `description` and an `owner` to every model or table in its schema file.
- Document every column whose meaning is not obvious from its name.
- Tag every table with one classification: `public`, `internal`, `confidential`, or `restricted`.
- Declare a freshness limit for every source and pipeline (for example dbt `freshness`), and alert when it is exceeded by 2x.
- Tag tables with no queries in 90 days as deprecated, and delete them only after a 30-day notice.
