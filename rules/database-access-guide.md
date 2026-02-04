---
trigger: model_decision
glob: database-access-guide
description: safe, efficient, maintainable DB access.
---

# Database Access Rule

**Purpose:** Safe, efficient, maintainable DB access.

**Rules:**

- Use repository/DAO layer; no direct DB calls in business logic.
- Prefer ORM; raw SQL only if necessary, always parameterized.
- Batch queries; avoid N+1 problems.
- Use caching carefully; keep invalidation consistent.
- Use separate schema per project.
- Run `EXPLAIN` for complex queries; save in `sqlplans`.

**Violations:**

- Unsafe SQL or in business logic.
- Repeated queries/N+1 issues.
- Mutable DB state leaks outside DAL.
