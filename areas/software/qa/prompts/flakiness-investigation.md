---
workflow: flakiness-investigation
---

# Prompt: `/flakiness-investigation`

Use when: a test fails intermittently in CI without a deterministic cause.

---

## Example 1 — Timeout-pattern flake

**EN:**
```
/flakiness-investigation

Flaky test: tests/e2e/checkout.spec.ts → "should complete payment flow"
Failure rate: 15% over last 20 CI runs (3/20 failed)
Pattern: only fails in CI, not locally; always on the payment confirmation step
Error: Timeout waiting for "Order confirmed" text (30s timeout exceeded)
Suspected cause: CI payment mock slower than local; or race condition in status polling
Last stable: 2 weeks ago before adding retry logic to payment service
```

**RU:**
```
/flakiness-investigation

Нестабильный тест: tests/e2e/checkout.spec.ts → "should complete payment flow"
Частота сбоев: 15% за последние 20 CI запусков (3/20 упали)
Паттерн: падает только в CI, не локально; всегда на шаге подтверждения платежа
Ошибка: Timeout ожидания текста "Order confirmed" (превышен таймаут 30с)
Предполагаемая причина: CI платёжный mock медленнее локального; или race condition в polling статуса
Последняя стабильная версия: 2 недели назад до добавления retry логики в payment service
```

---

## Example 2 — Test pollution flake

**EN:**
```
/flakiness-investigation

Flaky test: test_user_order_count_is_zero
Failure rate: 20% (always fails when test_create_bulk_orders runs before it)
Pattern: order-dependent failure — shared DB state between tests
Root cause suspected: test_create_bulk_orders commits data that isn't cleaned up
Fix direction: switch from truncation-based to transaction-rollback isolation
```

**RU:**
```
/flakiness-investigation

Нестабильный тест: test_user_order_count_is_zero
Частота сбоев: 20% (всегда падает когда test_create_bulk_orders запускается перед ним)
Паттерн: зависимость от порядка — общее состояние БД между тестами
Предполагаемая причина: test_create_bulk_orders коммитит данные которые не очищаются
Направление исправления: переключиться с truncation-based на transaction-rollback изоляцию
```
