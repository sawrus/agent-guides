```yaml
# Prompt: Backend Feature Implementation
workflow: feature-implementation-flow

# Context
feature_request: >
  Add a "refund_order" endpoint.
  - Input: order_id, reason
  - Logic: Check if order is PAID. If yes, create transaction, update status to REFUNDED, emit event.
  - If order is not PAID, return 400.

# Constraints
existing_codebase: ./src
```
