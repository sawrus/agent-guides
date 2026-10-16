---
name: dbt-patterns
description: "Provides dbt development patterns for materialization strategy, incremental models, and audit-column macros; use when building dbt models, writing macros, or configuring materializations."
---

# Skill: dbt Development Patterns

## When to load

When building dbt models, writing macros, or configuring materializations.

## Materialization Strategy

| Layer | Materialization | Why |
|:---|:---|:---|
| `staging/` | `view` | Always reflects source |
| `intermediate/` | `ephemeral` | Reduce clutter |
| `marts/` | `table` or `incremental` | Pre-computed for BI |

## Incremental Model

```sql
{{
    config(
        materialized='incremental',
        unique_key='order_id',
        incremental_strategy='merge',
        partition_by={'field': 'order_date', 'data_type': 'date'},
    )
}}

SELECT order_id, user_id, order_date, total_amount
FROM {{ ref('stg_orders') }}

{% if is_incremental() %}
    WHERE order_date >= (SELECT MAX(order_date) FROM {{ this }}) - INTERVAL '3 days'
{% endif %}
```

## Audit Columns Macro

```sql
{% macro audit_columns() %}
    CURRENT_TIMESTAMP AS loaded_at,
    '{{ invocation_id }}' AS dbt_invocation_id,
    '{{ this.name }}' AS dbt_model
{% endmacro %}
```
