---
workflow: slo-review
---

# Prompt: `/slo-review`

Use when: reviewing SLO health, error budget burn, and upcoming capacity risks before committing to reliability or scaling work.

---

## Example 1 — Q4 SLO review for 6 services

**EN:**
```
/slo-review

Review period: Q3 2024 (July–September)
Services under review: checkout, payment, order, auth, user, notification
Data available in Prometheus (Sloth recording rules)
For each service, evaluate:
  1. SLI achievement: actual ratio vs SLO target for the quarter
  2. Error budget burn: how much was consumed, main events causing consumption
  3. Incidents: count, severity, duration, correlation with budget consumption
  4. Target calibration: is the target too tight (budget always exhausted) or too loose (never burns)?
  5. Action items from previous review: completed? effective?
Recommendations needed:
  - Services to tighten (budget never used → target probably too conservative)
  - Services to loosen (budget always exhausted → target not achievable with current architecture)
  - Reliability investments for Q4 (prioritised by error budget consumed)
Output format: executive summary + per-service table + Q4 recommendations
```

**RU:**
```
/slo-review

Период проверки: Q3 2024 (июль–сентябрь)
Сервисы на проверке: checkout, payment, order, auth, user, notification
Данные доступны в Prometheus (Sloth recording rules)
Для каждого сервиса оценить:
  1. Достижение SLI: фактическое соотношение vs цель SLO за квартал
  2. Сжигание error budget: сколько потрачено, основные события вызвавшие потребление
  3. Инциденты: количество, severity, продолжительность, корреляция с потреблением бюджета
  4. Калибровка цели: слишком жёсткая (бюджет всегда исчерпан) или слишком мягкая (никогда не горит)?
  5. Action items из предыдущего review: выполнены? эффективны?
Необходимые рекомендации:
  - Сервисы для ужесточения (бюджет никогда не расходуется → цель вероятно слишком консервативная)
  - Сервисы для смягчения (бюджет всегда исчерпан → цель недостижима с текущей архитектурой)
  - Инвестиции в надёжность на Q4 (приоритизированы по потреблённому error budget)
Формат вывода: executive summary + таблица по сервисам + рекомендации на Q4
```

---

## Example 2 — Emergency SLO calibration after infra migration

**EN:**
```
/slo-review

Context: migrated from single-AZ to multi-AZ K8s (3 control plane + 6 workers)
Pre-migration: payment-service SLO 99.5%, frequently in Freeze state
Hypothesis: new HA setup should enable tightening to 99.9%
Task:
  1. Review pre-migration error budget consumption (last 3 months)
  2. Classify error budget events: infra-caused vs app-caused vs dependency-caused
  3. Estimate: if all infra-caused events are eliminated, what availability % would have been achieved?
  4. Propose new SLO target with rationale
  5. Set review checkpoint: evaluate new target after 30 days
```

**RU:**
```
/slo-review

Контекст: миграция с single-AZ на multi-AZ K8s (3 control plane + 6 workers)
До миграции: payment-service SLO 99.5%, часто в состоянии Freeze
Гипотеза: новая HA конфигурация должна позволить ужесточить до 99.9%
Задача:
  1. Проверить потребление error budget до миграции (последние 3 месяца)
  2. Классифицировать события error budget: вызванные инфрой / приложением / зависимостями
  3. Оценить: если бы все события вызванные инфрой были исключены, какой % доступности был бы достигнут?
  4. Предложить новую цель SLO с обоснованием
  5. Установить точку проверки: оценить новую цель через 30 дней
```

---

## Example 3 — Black Friday capacity runbook

**EN:**
```
/slo-review

Event: Black Friday (peak 5× normal traffic, 4-hour window)
Services affected: checkout, payment, order (top 3 by load)
Normal peak: 800 RPS; expected BF peak: 4000 RPS
Pre-event checklist needed:
  - Scale workers from 6 → 10 (pre-provision 48h before event)
  - Set HPA min replicas: checkout→10, payment→8, order→8 (prevent cold start during spike)
  - Pre-warm: connection pools, DNS TTLs flushed, CDN cache warmed
  - Load test: k6 script targeting 4500 RPS (10% above expected peak); run 2 days before
  - DB: pre-warm vacuumed + analysed; connection pool max set to 80% of max_connections
  - War room: open 1h before event; on-call + dev leads + DBA on standby
  - Auto-scale-down: trigger 2h after event peak (cost control)
Output: runbook document + pre-event checklist + post-event scale-down procedure
```

**RU:**
```
/slo-review

Событие: Чёрная пятница (пик 5× нормального трафика, 4-часовое окно)
Затронутые сервисы: checkout, payment, order (топ-3 по нагрузке)
Нормальный пик: 800 RPS; ожидаемый пик ЧП: 4000 RPS
Необходимый чеклист перед событием:
  - Масштабировать workers с 6 → 10 (заранее за 48ч до события)
  - Установить HPA min replicas: checkout→10, payment→8, order→8 (предотвратить cold start при скачке)
  - Pre-warm: connection pools, сброс DNS TTL, прогрев CDN кэша
  - Нагрузочное тестирование: k6 скрипт на 4500 RPS (10% сверх ожидаемого пика); запустить за 2 дня
  - БД: прогрев vacuum + analyse; max connection pool = 80% от max_connections
  - Военная комната: открыть за 1ч до события; on-call + dev leads + DBA в режиме ожидания
  - Авто-уменьшение масштаба: через 2ч после пика события (контроль затрат)
Результат: runbook документ + чеклист до события + процедура уменьшения масштаба после события
```
