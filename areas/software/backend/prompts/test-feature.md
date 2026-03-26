---
workflow: test-feature
---

# Prompt: `/test-feature`

Use when: expanding test coverage for an existing feature that is undertested or has known coverage gaps.

---

## Example 1 — Critical Business Flow

**EN:**
```
/test-feature "Payment processing coverage gaps"

Feature scope: payment-service — charge, refund, dispute flows
Current coverage: 38% (only happy path unit tests)
Critical gaps:
- No tests for partial refund edge cases (amount > original, amount = 0)
- No tests for payment provider timeout handling
- No tests for idempotency key collision
- No integration tests for charge → refund round-trip
Acceptance: coverage ≥ 70% on payment domain; all failure paths have explicit assertions
```

**RU:**
```
/test-feature "Покрытие критических сценариев обработки платежей"

Скоуп: payment-service — charge, refund, dispute flows
Текущее покрытие: 38% (только happy path unit tests)
Критические пробелы:
- Нет тестов для edge cases частичного возврата (amount > оригинала, amount = 0)
- Нет тестов для обработки таймаута от платёжного провайдера
- Нет тестов для коллизии idempotency key
- Нет integration tests для round-trip charge → refund
Критерий: покрытие ≥ 70% на payment domain; для всех failure paths — явные assertions
```

---

## Example 2 — API Contract Testing

**EN:**
```
/test-feature "Contract tests for Orders API public endpoints"

Endpoints: POST /orders, GET /orders/{id}, PATCH /orders/{id}/status, DELETE /orders/{id}
Missing test scenarios:
- 400 responses: invalid input shapes, missing required fields
- 401/403: unauthenticated, wrong scope, other user's order
- 404: non-existent order ID
- 409: concurrent status update conflict
Constraints: use existing test client; no new test infrastructure; stable in CI
```

**RU:**
```
/test-feature "Contract tests для публичных эндпоинтов Orders API"

Эндпоинты: POST /orders, GET /orders/{id}, PATCH /orders/{id}/status, DELETE /orders/{id}
Отсутствующие сценарии:
- 400 ответы: невалидные данные, отсутствующие обязательные поля
- 401/403: без аутентификации, неверный scope, чужой заказ
- 404: несуществующий order ID
- 409: конфликт при одновременном изменении статуса
Ограничения: использовать существующий test client; без новой test infrastructure; стабильно в CI
```

---

## Example 3 — Quick / Minimal

**EN:**
```
/test-feature "Add unit tests for DiscountCalculator service"

Current state: 0 tests; 3 methods: applyPercentage, applyFixed, applyCode
Cover: valid inputs, zero discount, negative discount guard, code not found case.
```

**RU:**
```
/test-feature "Unit tests для DiscountCalculator service"

Текущее состояние: 0 тестов; 3 метода: applyPercentage, applyFixed, applyCode
Покрыть: валидные входные данные, нулевая скидка, защита от отрицательной скидки, case code not found.
```
