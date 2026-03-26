---
workflow: backend-project-full-cycle
---

# Prompt: `/backend-project-full-cycle`

Use when: scaffolding a new Python/FastAPI backend service from scratch — architecture plan, project structure, Makefile, CI, and initial domain implementation.

---

## Example 1 — Domain API service

**EN:**
```
/backend-project-full-cycle

Project name: order-service
Directory: src/
Business logic:
  - Create Order (status: Draft → Paid → Cancelled / Refunded)
  - Add / remove Order Items (product_id, quantity, unit_price)
  - Pay Order — validate item availability, create payment record, emit OrderPaid event
  - Cancel Order — only if status is Draft or Paid (not Refunded)
  - List Orders for a user with cursor pagination (limit 20 default)
Tech stack:
  language: Python 3.12
  framework: FastAPI (async)
  database: PostgreSQL 16 via SQLAlchemy (async) + Alembic
  messaging: RabbitMQ (pika-async) for outbound events
  task queue: none (synchronous only for now)
  testing: pytest + pytest-asyncio + httpx
  CI: GitHub Actions
Non-functional: all DB operations async; Pydantic BaseSettings for config;
                structured JSON logs (structlog); Makefile with install/dev/test/lint/fmt targets
```

**RU:**
```
/backend-project-full-cycle

Название проекта: order-service
Директория: src/
Бизнес логика:
  - Создание Заказа (статус: Draft → Paid → Cancelled / Refunded)
  - Добавление / удаление позиций заказа (product_id, quantity, unit_price)
  - Оплата заказа — валидация доступности позиций, создание записи платежа, отправка события OrderPaid
  - Отмена заказа — только если статус Draft или Paid (не Refunded)
  - Список заказов пользователя с cursor пагинацией (по умолчанию limit 20)
Стек технологий:
  язык: Python 3.12
  фреймворк: FastAPI (async)
  база данных: PostgreSQL 16 через SQLAlchemy (async) + Alembic
  сообщения: RabbitMQ (pika-async) для исходящих событий
  очередь задач: нет (только синхронно пока)
  тестирование: pytest + pytest-asyncio + httpx
  CI: GitHub Actions
Нефункциональные: все операции с БД async; Pydantic BaseSettings для конфигурации;
                  структурированные JSON логи (structlog); Makefile с targets install/dev/test/lint/fmt
```

---

## Example 2 — Internal tool / simple CRUD

**EN:**
```
/backend-project-full-cycle

Project name: inventory-service
Directory: src/
Business logic:
  - CRUD for Products (name, sku, price, stock_quantity)
  - Stock reservation: reserve N units for an order (atomic, prevents oversell)
  - Stock release: release reserved units (on order cancel)
  - Low-stock alert: GET /products/low-stock returns products where stock < threshold
Tech stack:
  language: Python 3.12
  framework: FastAPI
  database: PostgreSQL via SQLAlchemy async
  messaging: none
  testing: pytest
  CI: GitLab CI
Scale: internal service, ~100 req/min peak, no need for caching yet
No auth: internal network only (API key via X-API-Key header is sufficient)
```

**RU:**
```
/backend-project-full-cycle

Название проекта: inventory-service
Директория: src/
Бизнес логика:
  - CRUD для Products (name, sku, price, stock_quantity)
  - Резервирование запасов: зарезервировать N единиц для заказа (атомарно, предотвращает oversell)
  - Освобождение запасов: освободить зарезервированные единицы (при отмене заказа)
  - Алерт о низком запасе: GET /products/low-stock возвращает продукты где stock < threshold
Стек технологий:
  язык: Python 3.12
  фреймворк: FastAPI
  база данных: PostgreSQL через SQLAlchemy async
  сообщения: нет
  тестирование: pytest
  CI: GitLab CI
Масштаб: внутренний сервис, ~100 req/min в пике, кэширование пока не нужно
Без auth: только внутренняя сеть (API ключ через заголовок X-API-Key достаточно)
```

---

## Example 3 — Minimal / Quick scaffold

**EN:**
```
/backend-project-full-cycle

Project name: webhook-receiver
Directory: .
Business logic:
  - Receive POST /webhooks/{provider} with HMAC signature verification
  - Store raw payload to PostgreSQL (table: webhook_events)
  - Enqueue for processing (Redis list: webhook_queue)
  - GET /webhooks/{id} to check processing status
Tech stack: Python 3.12, FastAPI, PostgreSQL, Redis, pytest, GitHub Actions
Keep minimal: no domain layers needed — single service file is fine; focus on correctness
```

**RU:**
```
/backend-project-full-cycle

Название проекта: webhook-receiver
Директория: .
Бизнес логика:
  - Приём POST /webhooks/{provider} с верификацией HMAC подписи
  - Сохранение сырого payload в PostgreSQL (таблица: webhook_events)
  - Постановка в очередь для обработки (Redis list: webhook_queue)
  - GET /webhooks/{id} для проверки статуса обработки
Стек: Python 3.12, FastAPI, PostgreSQL, Redis, pytest, GitHub Actions
Минималистично: слои домена не нужны — один service файл подойдёт; фокус на корректности
```
