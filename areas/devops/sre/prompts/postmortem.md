---
workflow: postmortem
---

# Prompt: `/postmortem`

Use when: writing or facilitating a blameless postmortem after a P0/P1 incident.

---

## Example 1 — Full postmortem from incident data

**EN:**
```
/postmortem

Incident: INC-2024-112 / Service: payment-service / Severity: P1
Duration: 2024-11-15 03:42–04:01 UTC (19 min)
Impact: 4.2% error rate; ~850 failed payment attempts; SLO: 18 min budget consumed
Root cause (preliminary): OOMKilled pods after v2.4.1 deploy introduced high-memory code path

Timeline (from scribe doc):
  03:42 - Alert fired HighErrorRate 4.2%
  03:44 - On-call acknowledged
  03:49 - Identified: payment-service pods OOMKilling (exit 137)
  03:51 - Mitigation: helm rollback payment-service to revision 3
  03:53 - Error rate dropping
  04:01 - Resolved; monitoring

Tasks:
  1. Full 5-whys RCA from the preliminary root cause
  2. Contributing factors analysis
  3. 3–5 action items (specific, owned, dated within 2 weeks)
  4. What went well section (at least 3 items)
  5. SLO impact calculation
```

**RU:**
```
/postmortem

Инцидент: INC-2024-112 / Сервис: payment-service / Severity: P1
Длительность: 2024-11-15 03:42–04:01 UTC (19 мин)
Влияние: error rate 4.2%; ~850 неудачных попыток оплаты; SLO: потрачено 18 мин бюджета
Корневая причина (предварительно): OOMKilled поды после деплоя v2.4.1 с высокопамятным кодом

Timeline (из scribe doc):
  03:42 - Алерт сработал HighErrorRate 4.2%
  03:44 - On-call подтвердил
  03:49 - Определено: поды payment-service OOMKilling (exit 137)
  03:51 - Митигация: helm rollback payment-service до ревизии 3
  03:53 - Error rate падает
  04:01 - Разрешено; мониторинг

Задачи:
  1. Полный анализ 5-whys от предварительной корневой причины
  2. Анализ способствующих факторов
  3. 3–5 action items (конкретные, с владельцами, сроки в течение 2 недель)
  4. Раздел "что прошло хорошо" (минимум 3 пункта)
  5. Расчёт влияния на SLO
```

---

## Example 2 — SLO review: define SLOs for new service

**EN:**
```
/postmortem

Task: define SLOs (not a postmortem — SLO design session)
Service: notification-service
User expectation: "Notifications arrive within 30 seconds; don't lose notifications"
Current metrics available: delivery_attempts_total, delivery_success_total, delivery_latency_seconds
Team size: 2 backend engineers + 1 devops
Target tier: Tier 2 (internal tool; not directly revenue-impacting)
Design:
  1. Select 2 SLIs (availability + latency) with formulas
  2. Propose SLO targets (start conservative)
  3. Calculate error budget for 28-day window
  4. Write burn rate alert thresholds (fast + slow)
  5. Sloth YAML definition
```

**RU:**
```
/postmortem

Задача: определить SLO (не postmortem — сессия проектирования SLO)
Сервис: notification-service
Ожидание пользователей: "Уведомления доставляются в течение 30 секунд; уведомления не теряются"
Доступные метрики: delivery_attempts_total, delivery_success_total, delivery_latency_seconds
Размер команды: 2 backend инженера + 1 devops
Целевой tier: Tier 2 (внутренний инструмент; не влияет напрямую на выручку)
Проектирование:
  1. Выбрать 2 SLI (availability + latency) с формулами
  2. Предложить цели SLO (начать консервативно)
  3. Рассчитать error budget для 28-дневного окна
  4. Написать пороги burn rate алертов (быстрый + медленный)
  5. YAML определение для Sloth
```
