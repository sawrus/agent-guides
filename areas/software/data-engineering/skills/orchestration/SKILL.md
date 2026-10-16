---
name: orchestration
description: "Provides Airflow DAG templates and idempotent task patterns for pipeline orchestration; use when designing DAGs, debugging pipeline failures, or configuring retries."
---

# Skill: Pipeline Orchestration (Airflow)

## When to load

When designing DAGs, debugging pipeline failures, or configuring retries.

## DAG Template

```python
with DAG(
    dag_id="orders_pipeline",
    default_args={
        "owner": "data-platform",
        "retries": 3,
        "retry_delay": timedelta(minutes=5),
        "retry_exponential_backoff": True,
        "email_on_failure": True,
    },
    schedule="0 4 * * *",
    catchup=False,          # ← Never True; causes backfill avalanche
    max_active_runs=1,      # Prevent concurrent runs
) as dag:
    ...
```

## Idempotent Task Pattern

```python
def load_orders(execution_date: str, **context):
    """Safe to retry: DELETE + INSERT on target partition."""
    partition = execution_date[:10]
    with warehouse.connect() as conn:
        conn.execute(f"DELETE FROM stg_orders WHERE order_date = '{partition}'")
        conn.execute(f"INSERT INTO stg_orders SELECT * FROM raw_orders WHERE DATE(created_at) = '{partition}'")
```
