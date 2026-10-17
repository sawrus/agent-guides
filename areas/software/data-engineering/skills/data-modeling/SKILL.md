---
name: data-modeling
description: "Guides warehouse data modeling with a Kimball/wide-table/Data Vault decision tree, medallion dbt layering, and fact table templates; use when designing a warehouse schema, choosing a modeling approach, or refactoring an existing model."
---

# Skill: Data Modeling

## When to load

When designing a warehouse schema, choosing between modeling approaches, or refactoring an existing model.

## Approach Decision Tree

```
Primary consumer?
  → BI tools + analysts: Kimball (dimensional)
  → Data science + ML: Wide denormalized tables
  → Multiple teams: Data Vault

History tracking?
  → Never/rarely: Type 1 SCD (overwrite)
  → Track current + previous: Type 2 SCD (versioned rows)

Scale?
  → < 100 GB: Simple star schema
  → 100 GB – 10 TB: Partitioned star schema
  → > 10 TB: Data Vault or Lakehouse (Delta/Iceberg)
```

## dbt Layering (Medallion Architecture)

```
sources/       ← Raw data as-is from source systems
staging/       ← Cleaned, renamed, typed. 1:1 with source tables.
intermediate/  ← Business logic, joins. Not exposed directly.
marts/         ← Dimensional models for specific use cases
  ├── core/    ← fct_*, dim_*
  └── finance/ ← rpt_*
```

## Fact Table Template

```sql
CREATE TABLE fct_orders (
    order_key    BIGINT PRIMARY KEY,  -- surrogate key
    order_id     VARCHAR NOT NULL,    -- natural key
    user_key     BIGINT REFERENCES dim_users(user_key),
    date_key     INT REFERENCES dim_date(date_key),
    quantity     INT NOT NULL,
    total_amount NUMERIC(10,2) NOT NULL,
    loaded_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_system VARCHAR DEFAULT 'orders-api'
);
```
