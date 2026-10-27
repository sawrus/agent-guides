---
description: Breaking and safe schema changes for warehouse tables and streaming topics.
paths:
  - "**/models/**"
  - "**/migrations/**"
  - "**/*.avsc"
  - "**/*.proto"
---

# Schema management

- Version the table as breaking when you rename or drop a column, change a type incompatibly, add a `NOT NULL` column without a default, or change the partition key.
- Ship a breaking change on a table with external consumers as a new versioned table (`orders_v2`) and keep the old version for at least 30 days.
- Add new columns as nullable or with a default value.
- Register every streaming topic schema in a schema registry and set its compatibility mode to `BACKWARD` or stricter.
- Validate messages against the registered schema in the producer before publish.
- Run the schema compatibility check in CI for every changed `.avsc` or `.proto` file.
