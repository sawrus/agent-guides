---
name: sql-optimization
description: "Applies SQL optimization patterns, window functions, and Snowflake-specific tuning; use when writing complex queries, optimizing slow queries, designing indexes, or reviewing query performance."
---

# Skill: SQL Optimization

## When to load

When writing complex queries, optimizing slow queries, designing indexes, or reviewing query performance.

## Core Patterns

```sql
-- ✅ Column projection — never SELECT *
SELECT user_id, created_at, total_amount FROM orders WHERE created_at >= '2026-01-01';

-- ✅ Partition pruning — filter on partition column first
SELECT user_id, total_amount
FROM orders
WHERE order_date = '2026-01-15'  -- partition filter first
  AND status = 'completed';

-- ❌ Function on indexed column defeats index
WHERE DATE(created_at) = '2026-01-15'
-- ✅ Range comparison preserves index
WHERE created_at >= '2026-01-15' AND created_at < '2026-01-16'
```

## Window Functions (prefer over self-joins)

```sql
SELECT
    user_id, order_date, amount,
    SUM(amount) OVER (
        PARTITION BY user_id ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_amount,
    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_date DESC) AS recency_rank
FROM orders;
```

## Snowflake-Specific

```sql
-- Cluster keys on large tables (> 1 TB)
ALTER TABLE orders CLUSTER BY (order_date, status);

-- COPY INTO for bulk loads — never row-by-row INSERT
COPY INTO orders FROM @my_stage/orders/
FILE_FORMAT = (TYPE = PARQUET) MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE;
```
