---
workflow: debug-issue
---

# Prompt: `/debug-issue`

Use when: investigating and resolving a backend defect, incident, or unexpected behavior.

---

## Example 1 — Production Incident

**EN:**
```
/debug-issue "Orders API 500 errors spike — P1"

Severity: P1
Symptoms: 500 error rate on POST /orders jumped from 0.1% to 8% at 14:32 UTC
Affected service: order-service (v2.4.1, deployed 14:15 UTC)
Logs: attached — shows NullPointerException in OrderService.createOrder() line 142
Metrics: error spike matches deployment time; CPU and memory normal
Last change: added optional discount_code field to order creation
Expected: reproduce and fix; write regression test; document root cause
```

**RU:**
```
/debug-issue "Спайк 500 ошибок в Orders API — P1"

Severity: P1
Симптомы: rate 500 ошибок на POST /orders вырос с 0.1% до 8% в 14:32 UTC
Сервис: order-service (v2.4.1, задеплоен в 14:15 UTC)
Логи: приложены — NullPointerException в OrderService.createOrder() строка 142
Метрики: спайк совпадает со временем деплоя; CPU и memory в норме
Последнее изменение: добавлено опциональное поле discount_code
Ожидание: воспроизвести и исправить; написать regression test; задокументировать причину
```

---

## Example 2 — Intermittent Bug

**EN:**
```
/debug-issue "Duplicate order creation on payment webhook retry"

Severity: P2
Symptoms: ~0.3% of orders created twice when payment provider retries webhook
Frequency: intermittent, only on webhook retry (payment provider retries 3x on timeout)
Suspected cause: webhook handler is not idempotent — processes same payment_id twice
Expected: implement idempotency check on payment_id; add regression test with concurrent request simulation
```

**RU:**
```
/debug-issue "Дублирование заказов при повторном вебхуке оплаты"

Severity: P2
Симптомы: ~0.3% заказов создаётся дважды при retry от платёжного провайдера
Частота: intermittent, только при retry (провайдер делает 3 попытки при таймауте)
Предполагаемая причина: обработчик вебхука не idempotent — обрабатывает один payment_id дважды
Ожидание: добавить проверку идемпотентности по payment_id; тест с симуляцией конкурентных запросов
```

---

## Example 3 — Quick / Minimal

**EN:**
```
/debug-issue "GET /products returns 403 for service account token"

Service account role: product-reader
Expected: 200 with product list
Actual: 403 Forbidden
Started: after auth service upgrade to v3.1.0 yesterday
```

**RU:**
```
/debug-issue "GET /products возвращает 403 для service account токена"

Роль service account: product-reader
Ожидалось: 200 со списком продуктов
Факт: 403 Forbidden
Началось: после обновления auth service до v3.1.0 вчера
```
