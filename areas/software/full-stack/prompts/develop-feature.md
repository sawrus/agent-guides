---
workflow: develop-feature
---

# Prompt: `/develop-feature`

Use when: implementing a feature end-to-end in an existing full-stack Python/FastAPI + Next.js project — DB model through API to UI.

---

## Example 1 — Full-stack feature with DB and UI

**EN:**
```
/develop-feature

Feature: "Product wishlists"
Stack: FastAPI (Python 3.12) + SQLAlchemy async + Next.js (App Router) + Tailwind
Acceptance criteria:
  - Users can add / remove products from their wishlist (POST/DELETE /api/v1/wishlist/{product_id})
  - GET /api/v1/wishlist returns user's wishlist (paginated, cursor-based)
  - Product detail page shows "Add to wishlist" / "Remove" button (heart icon) — auth required to use
  - Wishlist page (/wishlist) lists all saved products with thumbnail, name, price
  - Wishlist count shown in navigation header (badge)
DB changes: create wishlist_items table (user_id, product_id, created_at); unique constraint
Constraints: wishlist is user-scoped (cannot see others'); limit 500 items per user
Tests: service unit tests (add duplicate = 409, over limit = 400) + API integration + E2E (add → see on page)
```

**RU:**
```
/develop-feature

Фича: "Списки желаний продуктов"
Стек: FastAPI (Python 3.12) + SQLAlchemy async + Next.js (App Router) + Tailwind
Критерии приёмки:
  - Пользователи могут добавлять / удалять продукты из списка желаний (POST/DELETE /api/v1/wishlist/{product_id})
  - GET /api/v1/wishlist возвращает список желаний пользователя (пагинация, cursor-based)
  - Страница продукта показывает кнопку "Добавить в список желаний" / "Убрать" (иконка сердца) — для использования требуется auth
  - Страница /wishlist перечисляет все сохранённые продукты с миниатюрой, названием, ценой
  - Количество в списке желаний отображается в навигационном заголовке (badge)
Изменения БД: создать таблицу wishlist_items (user_id, product_id, created_at); уникальное ограничение
Ограничения: список желаний привязан к пользователю (нельзя видеть чужие); лимит 500 позиций на пользователя
Тесты: unit тесты сервиса (добавить дубликат = 409, превышение лимита = 400) + API интеграция + E2E (добавить → увидеть на странице)
```

---

## Example 2 — API-only feature (no frontend)

**EN:**
```
/develop-feature

Feature: "Bulk order status update (admin API)"
Stack: FastAPI + SQLAlchemy async (no UI changes)
Endpoint: PATCH /api/v1/admin/orders/bulk-status
Auth: admin role required (scope: admin:orders:write)
Request: { order_ids: list[int] (max 100), status: OrderStatus, reason: str }
Business rules:
  - All order_ids must belong to the same tenant (400 if mixed tenants)
  - Only allowed transitions: PENDING → PROCESSING, PROCESSING → SHIPPED
  - Invalid transition returns 422 with per-order error detail
  - Successful updates emit OrderStatusChanged event per order
  - Returns: { updated: int, failed: list[{order_id, error}] } (partial success allowed)
DB: bulk UPDATE with RETURNING; wrap in single transaction (all-or-nothing if any fail: configurable)
Tests: test partial failure scenario; test tenant isolation; test unauthorised access (403)
```

**RU:**
```
/develop-feature

Фича: "Массовое обновление статуса заказов (admin API)"
Стек: FastAPI + SQLAlchemy async (без изменений UI)
Эндпоинт: PATCH /api/v1/admin/orders/bulk-status
Auth: требуется роль admin (scope: admin:orders:write)
Запрос: { order_ids: list[int] (макс 100), status: OrderStatus, reason: str }
Бизнес правила:
  - Все order_ids должны принадлежать одному tenant (400 если смешанные tenants)
  - Разрешённые переходы только: PENDING → PROCESSING, PROCESSING → SHIPPED
  - Недопустимый переход возвращает 422 с детализацией ошибок по заказу
  - Успешные обновления отправляют событие OrderStatusChanged на каждый заказ
  - Возвращает: { updated: int, failed: list[{order_id, error}] } (частичный успех допускается)
БД: массовый UPDATE с RETURNING; обернуть в одну транзакцию (всё или ничего при любом сбое: настраивается)
Тесты: тест сценария частичного сбоя; тест изоляции tenant; тест несанкционированного доступа (403)
```

---

## Example 3 — Quick / Small change

**EN:**
```
/develop-feature

Feature: "Archive products (soft-delete)"
Change scope: small — adds 'archived' status and filters
Endpoints affected:
  - PATCH /api/v1/products/{id}: add {"status": "archived"} as valid transition (admin only)
  - GET /api/v1/products: exclude archived by default; add ?include_archived=true param for admin
DB: add archived_at TIMESTAMP column to products (nullable; non-breaking migration)
No frontend changes needed (admin uses API directly)
Tests: verify archived products hidden from public listing; visible to admin with param
```

**RU:**
```
/develop-feature

Фича: "Архивирование продуктов (soft-delete)"
Скоуп изменения: небольшой — добавляет статус 'archived' и фильтры
Затронутые эндпоинты:
  - PATCH /api/v1/products/{id}: добавить {"status": "archived"} как допустимый переход (только admin)
  - GET /api/v1/products: исключать archived по умолчанию; добавить параметр ?include_archived=true для admin
БД: добавить столбец archived_at TIMESTAMP в products (nullable; non-breaking миграция)
Изменений frontend не нужно (admin использует API напрямую)
Тесты: убедиться что архивированные продукты скрыты из публичного листинга; видны admin с параметром
```
