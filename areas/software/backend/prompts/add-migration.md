---
workflow: add-migration
---

# Prompt: `/add-migration`

Use when: adding or modifying database schema — columns, tables, indexes, constraints.

---

## Example 1 — Breaking Change (Expand/Contract)

**EN:**
```
/add-migration "Rename users.full_name to users.display_name"

Change type: breaking — column rename
Affected services: user-service (writes), profile-service (reads), search-service (reads)
Current column: users.full_name VARCHAR(255) NOT NULL
Target column: users.display_name VARCHAR(255) NOT NULL
Strategy: expand/contract
  Phase 1: add display_name column, backfill from full_name, write to both
  Phase 2: migrate all reader services to display_name
  Phase 3: mark full_name deprecated
  Phase 4 (30 days): drop full_name
Rollback: Phase 1 is reversible; document downgrade migration
```

**RU:**
```
/add-migration "Переименование users.full_name в users.display_name"

Тип изменения: breaking — переименование колонки
Затронутые сервисы: user-service (запись), profile-service (чтение), search-service (чтение)
Текущая колонка: users.full_name VARCHAR(255) NOT NULL
Целевая колонка: users.display_name VARCHAR(255) NOT NULL
Стратегия: expand/contract
  Фаза 1: добавить display_name, бэкфилл из full_name, писать в обе
  Фаза 2: перевести все читающие сервисы на display_name
  Фаза 3: пометить full_name как deprecated
  Фаза 4 (через 30 дней): удалить full_name
Rollback: Фаза 1 обратима; написать downgrade миграцию
```

---

## Example 2 — Non-Breaking Change

**EN:**
```
/add-migration "Add index on orders.created_at for date-range queries"

Change type: non-breaking — add index
Table: orders
New index: idx_orders_created_at ON orders(created_at DESC)
Reason: query GET /orders?from=&to= does full table scan; table has 50M rows
Validate: EXPLAIN ANALYZE on the query before and after
Deployment: can be applied with CONCURRENTLY in Postgres — no table lock
```

**RU:**
```
/add-migration "Добавить индекс на orders.created_at для range-запросов"

Тип изменения: non-breaking — добавление индекса
Таблица: orders
Новый индекс: idx_orders_created_at ON orders(created_at DESC)
Причина: запрос GET /orders?from=&to= делает full table scan; в таблице 50M строк
Валидация: EXPLAIN ANALYZE на запрос до и после
Деплой: применить с CONCURRENTLY в Postgres — без блокировки таблицы
```

---

## Example 3 — Quick / Minimal

**EN:**
```
/add-migration "Add archived_at nullable column to projects"

Table: projects
Change: add column archived_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NULL
Non-breaking; no existing queries affected; no data backfill needed.
```

**RU:**
```
/add-migration "Добавить nullable колонку archived_at в projects"

Таблица: projects
Изменение: добавить archived_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NULL
Non-breaking; существующие запросы не затронуты; бэкфилл не нужен.
```
