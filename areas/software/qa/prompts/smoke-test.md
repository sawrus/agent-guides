---
workflow: smoke-test
---

# Prompt: `/smoke-test`

Use when: validating a deployment is healthy immediately after it lands in an environment.

---

## Example 1 — Post-deploy validation

**EN:**
```
/smoke-test

Environment: staging
Deployment context: v2.4.1 just deployed — adds payment retry logic
Critical paths to verify:
- User can log in and see dashboard
- Product search returns results
- Add to cart → checkout → order confirmation flow completes
- Payment with test card 4242 4242 4242 4242 succeeds
Stop criteria: if payment flow fails → trigger rollback immediately
```

**RU:**
```
/smoke-test

Окружение: staging
Контекст деплоя: только что задеплоена v2.4.1 — добавлена логика повтора платежей
Критические пути для проверки:
- Пользователь может войти и видит dashboard
- Поиск продуктов возвращает результаты
- Поток добавить в корзину → оплата → подтверждение заказа завершается
- Оплата тестовой картой 4242 4242 4242 4242 проходит успешно
Критерий остановки: если поток оплаты падает → немедленно инициировать откат
```

---

## Example 2 — Pre-release smoke

**EN:**
```
/smoke-test

Environment: production (20% canary)
Deployment: canary traffic split active — v2.5.0 on 20% of traffic
Check: error rate and latency on canary pods vs. baseline pods (must be within 5%)
Auth: admin token from CI secrets
Timeout: 15 minutes max — block full rollout if not green
```

**RU:**
```
/smoke-test

Окружение: production (20% canary)
Деплой: активен canary split — v2.5.0 получает 20% трафика
Проверить: error rate и latency на canary подах vs. baseline (должны быть в пределах 5%)
Auth: admin токен из CI secrets
Таймаут: максимум 15 минут — блокировать полный rollout если не green
```
