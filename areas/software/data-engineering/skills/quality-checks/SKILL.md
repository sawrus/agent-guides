---
name: quality-checks
description: "Defines a dbt test taxonomy and volume anomaly detection for data quality; use when adding tests to dbt models, implementing data validation, or investigating data quality incidents."
---

# Skill: Data Quality Checks

## When to load

When adding tests to dbt models, implementing data validation, or investigating quality incidents.

## dbt Test Taxonomy

```yaml
models:
  - name: fct_orders
    columns:
      - name: order_key
        tests: [unique, not_null]
      - name: user_key
        tests:
          - not_null
          - relationships:
              to: ref('dim_users')
              field: user_key
      - name: total_amount
        tests:
          - not_null
          - dbt_utils.expression_is_true:
              expression: ">= 0"
      - name: order_status
        tests:
          - accepted_values:
              values: ['pending', 'processing', 'completed', 'cancelled']
    tests:
      - dbt_utils.recency:
          datepart: hour
          field: loaded_at
          interval: 4
```

## Volume Anomaly Detection

```sql
-- Alert when daily row count deviates > 3σ from 30-day rolling average
WITH stats AS (
    SELECT
        load_date, row_count,
        AVG(row_count) OVER (ORDER BY load_date ROWS BETWEEN 29 PRECEDING AND 1 PRECEDING) AS rolling_avg,
        STDDEV(row_count) OVER (ORDER BY load_date ROWS BETWEEN 29 PRECEDING AND 1 PRECEDING) AS rolling_std
    FROM daily_counts
)
SELECT *, CASE WHEN ABS(row_count - rolling_avg) > 3 * rolling_std THEN 'ANOMALY' ELSE 'OK' END AS status
FROM stats WHERE load_date = CURRENT_DATE - 1;
```
