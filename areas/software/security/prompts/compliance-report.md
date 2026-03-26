---
workflow: compliance-report
---

# Prompt: `/compliance-report`

Use when: generating a compliance evidence report for a specific framework (SOC 2, PCI-DSS, GDPR, ISO 27001) — mapping controls to evidence and identifying gaps.

---

## Example 1 — SOC 2 Type II readiness

**EN:**
```
/compliance-report

Framework: SOC 2 Type II (Trust Service Criteria: Security + Availability)
Scope: order-service, payment-service, user-service (production AWS environment)
Audit window: last 12 months
Evidence sources to collect:
  - Access control: IAM role assignments, MFA enforcement logs (AWS CloudTrail)
  - Change management: PR merge records, CI/CD pipeline logs (GitHub Actions)
  - Incident response: PagerDuty incident log, postmortem documents
  - Monitoring: CloudWatch alarm configs, uptime records (SLA: 99.9%)
  - Encryption: KMS key policies, S3 bucket encryption settings
Gaps from last audit: CC6.1 (access review not documented quarterly)
Output: compliance-report-soc2-2024.md — control matrix with evidence links + gap list
```

**RU:**
```
/compliance-report

Фреймворк: SOC 2 Type II (Trust Service Criteria: Security + Availability)
Скоуп: order-service, payment-service, user-service (production AWS окружение)
Период аудита: последние 12 месяцев
Источники доказательств для сбора:
  - Контроль доступа: назначения IAM ролей, логи соблюдения MFA (AWS CloudTrail)
  - Управление изменениями: записи мержа PR, логи CI/CD pipeline (GitHub Actions)
  - Реагирование на инциденты: лог инцидентов PagerDuty, документы postmortem
  - Мониторинг: конфигурации алармов CloudWatch, записи uptime (SLA: 99.9%)
  - Шифрование: политики KMS ключей, настройки шифрования S3 bucket
Пробелы с прошлого аудита: CC6.1 (ежеквартальный ревью доступа не задокументирован)
Результат: compliance-report-soc2-2024.md — матрица контролей со ссылками на доказательства + список пробелов
```

---

## Example 2 — GDPR data processing audit

**EN:**
```
/compliance-report

Framework: GDPR (EU) — Articles 13, 14, 17, 30
Concern: new analytics pipeline collects user behaviour events — need DPA review
Data flows to document:
  - User events → Kafka → ClickHouse (EU region) — retention 90 days
  - Aggregated reports → BigQuery (EU region) — retention 3 years
  - Raw events → S3 (EU region) — retention 30 days
PII in events: user_id (pseudonymised), session_id, country, browser
Legal basis: legitimate interest (analytics) — documented in privacy policy v3.2
Right to erasure: user_id hash deletion must cascade to ClickHouse + BigQuery
Output: Article 30 record of processing + erasure procedure + DPA checklist
```

**RU:**
```
/compliance-report

Фреймворк: GDPR (EU) — Статьи 13, 14, 17, 30
Озабоченность: новый analytics pipeline собирает события поведения пользователей — нужно ревью DPA
Потоки данных для документирования:
  - Пользовательские события → Kafka → ClickHouse (EU регион) — хранение 90 дней
  - Агрегированные отчёты → BigQuery (EU регион) — хранение 3 года
  - Сырые события → S3 (EU регион) — хранение 30 дней
PII в событиях: user_id (псевдоанонимизирован), session_id, country, browser
Правовое основание: законный интерес (аналитика) — задокументировано в политике конфиденциальности v3.2
Право на удаление: удаление хэша user_id должно каскадироваться в ClickHouse + BigQuery
Результат: Запись обработки по Статье 30 + процедура удаления + чеклист DPA
```

---

## Example 3 — Quick / PCI-DSS scope check

**EN:**
```
/compliance-report

Framework: PCI-DSS v4.0 — scope assessment only (not full audit)
Question: does our new in-app chat feature bring card data into PCI scope?
Context: chat allows users to type free text; could contain card numbers
Assessment needed:
  - Is chat text stored? Where? How long?
  - Is there PAN detection / masking on input?
  - Does Stripe.js token flow bypass our servers?
Output: scope determination (in-scope / out-of-scope) with justification + required controls if in-scope
```

**RU:**
```
/compliance-report

Фреймворк: PCI-DSS v4.0 — только оценка скоупа (не полный аудит)
Вопрос: попадает ли наша новая функция внутреннего чата в скоуп PCI из-за данных карт?
Контекст: чат позволяет пользователям вводить произвольный текст; может содержать номера карт
Необходимая оценка:
  - Хранится ли текст чата? Где? Как долго?
  - Есть ли обнаружение PAN / маскирование на вводе?
  - Обходит ли Stripe.js токен flow наши серверы?
Результат: определение скоупа (в скоупе / вне скоупа) с обоснованием + необходимые контроли если в скоупе
```
