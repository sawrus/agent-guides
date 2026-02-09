```yaml
# Prompt: New Backend Project
workflow: backend-project-full-cycle

# Project Details
project_name: order-service
project_dir: src
business_logic_description: >
  A service to manage customer orders.
  - Create Order (Draft)
  - Pay Order (Processing -> Paid)
  - Cancel Order
  - List Orders (with pagination)

# Tech Stack (Optional - Agent will ask if omitted)
tech_stack:
  language: Python 3.12
  framework: FastAPI
  database: PostgreSQL
  messaging: RabbitMQ
```
