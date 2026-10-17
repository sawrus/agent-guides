---
name: backend-developer
type: skill
description: Specialized skill for Python backend development using FastAPI, SQLAlchemy, and Pydantic.
inputs:
  - implementation_plan.md
  - feature_request
outputs:
  - python_code
related-rules:
  - backend-architecture-rule.md
  - code-style-guide.md
allowed-tools: Read, Write, Edit, Grep, Bash
---

# Backend Developer Skill

> **Expertise:** Python 3.12+, FastAPI, SQLAlchemy (Async), Pydantic V2, Pytest.

## 🧠 Mindset

- **Type Safety:** Uses strict type hints. `mypy` must pass.
- **Async First:** All I/O operations must be `async`.
- **Explicit/Implicit:** Prefer explicit dependency injection over global state.
- **Error Handling:** Catch specific exceptions, never bare `except Exception:`.

## 🛠️ Toolkit

| Category          | Library      | Usage                                     |
| :---------------- | :----------- | :---------------------------------------- |
| **Web Framework** | `fastapi`    | Routing, Dependency Injection, Validation |
| **ORM**           | `sqlalchemy` | Async ORM, Models                         |
| **Migrations**    | `alembic`    | Database schema versions                  |
| **Validation**    | `pydantic`   | Data transfer objects, settings           |
| **Testing**       | `pytest`     | Unit and Integration tests                |

## 📋 Implementation Checklist

1.  **Models & Migrations:**
    - Define SQLAlchemy models.
    - Generate migration: `alembic revision --autogenerate -m "desc"`.
    - **Verify architecture rules:** Models do not import from API.

2.  **Repositories:**
    - CRUD operations.
    - Return Pydantic models or ORM objects (depending on project pattern).

3.  **Services:**
    - Business logic.
    - Transaction management (`async with session.begin():`).

4.  **API:**
    - Status codes (201 for creation, 204 for no content).
    - Proper HTTP verbs.

5.  **Tests:**
    - Fixtures for DB session.
    - `client.post(...)` for API tests.
