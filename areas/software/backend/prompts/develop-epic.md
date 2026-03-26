---
workflow: develop-epic
---

# Prompt: `/develop-epic`

Use when: delivering a large multi-sprint epic that must be broken into independently deployable increments.

---

## Example 1 — New Domain Feature

**EN:**
```
/develop-epic "Multi-currency Support"

Epic goal: allow users to transact in USD, EUR, GBP, and JPY with real-time exchange rates
Increments (suggested):
  1. Currency model + exchange rate service integration (no UI)
  2. Price display in user's preferred currency
  3. Checkout and payment in selected currency
  4. Historical transaction display with original and converted amounts
Acceptance criteria (epic-level):
  - User can set preferred currency in profile
  - All price displays respect preferred currency
  - Payments processed in selected currency via Stripe multi-currency
  - Exchange rate updated every 15 minutes from provider
Non-goals: crypto currencies; manual rate override by admins (future epic)
Architecture risk: exchange rate service failure must not block checkout
```

**RU:**
```
/develop-epic "Поддержка нескольких валют"

Цель эпика: пользователи могут работать в USD, EUR, GBP, JPY с курсами в реальном времени
Инкременты (предложение):
  1. Модель валюты + интеграция сервиса курсов (без UI)
  2. Отображение цен в валюте пользователя
  3. Оформление и оплата в выбранной валюте
  4. История транзакций с оригинальной и конвертированной суммой
Критерии приёмки (уровень эпика):
  - Пользователь выбирает предпочтительную валюту в профиле
  - Все цены учитывают валюту пользователя
  - Платежи обрабатываются в выбранной валюте через Stripe multi-currency
  - Курс обновляется каждые 15 минут
Non-goals: криптовалюты; ручное управление курсами (следующий эпик)
Архитектурный риск: сбой сервиса курсов не должен блокировать оформление заказа
```

---

## Example 2 — Platform Improvement

**EN:**
```
/develop-epic "Event-Driven Architecture Migration for Order Processing"

Epic goal: migrate synchronous order processing chain to event-driven with Kafka
Current: OrderService → PaymentService → NotificationService (synchronous, 3s p99)
Target: OrderService emits events; Payment and Notification subscribe independently
Increments:
  1. Kafka infrastructure + event schema definitions
  2. Order service emits events (dual-write: sync + async during migration)
  3. Payment service migrated to consume events
  4. Notification service migrated; sync chain removed
Success metric: order creation p99 < 500ms; services independently deployable
```

**RU:**
```
/develop-epic "Миграция обработки заказов на Event-Driven Architecture"

Цель: перевести синхронную цепочку обработки заказов на Kafka
Текущее: OrderService → PaymentService → NotificationService (синхронно, p99 3s)
Цель: OrderService публикует события; Payment и Notification независимо подписываются
Инкременты:
  1. Kafka инфраструктура + схемы событий
  2. OrderService публикует события (dual-write во время миграции)
  3. PaymentService переведён на события
  4. NotificationService переведён; синхронная цепочка удалена
Метрика успеха: создание заказа p99 < 500ms; сервисы деплоятся независимо
```
