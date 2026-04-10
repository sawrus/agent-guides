---
workflow: security-scan
---

# Prompt: `/security-scan`

Use when: running a security scan that must produce actionable release decisions (`exploitable-now`, `not-reachable`, `accepted-risk`) rather than only raw scanner output.

---

## Example 1 — Release gate with reachability triage and VEX output

**EN:**
```
/security-scan

Trigger: release candidate v4.2.0
Scope: SAST + dependency + secrets + IaC
Stack: Node.js 22, Python 3.12, Terraform
Policy:
  - Block release for any Critical finding classified as exploitable-now
  - High findings require remediation plan <= 72h or time-bound exception
Required output sections:
  1) Findings summary by severity
  2) Reachability analysis for each High/Critical dependency CVE
  3) Classification table: exploitable-now / not-reachable / accepted-risk
  4) VEX-style statements for not-reachable items with evidence
  5) Exception register (owner, expiry, compensating controls)
```

**RU:**
```
/security-scan

Триггер: release candidate v4.2.0
Скоуп: SAST + зависимости + секреты + IaC
Стек: Node.js 22, Python 3.12, Terraform
Политика:
  - Блокировать релиз при любом Critical, классифицированном как exploitable-now
  - Для High нужен план устранения <= 72ч или ограниченное по времени исключение
Обязательные разделы результата:
  1) Сводка находок по серьёзности
  2) Reachability-анализ для каждого High/Critical dependency CVE
  3) Таблица классификации: exploitable-now / not-reachable / accepted-risk
  4) VEX-подобные записи для not-reachable с доказательствами
  5) Реестр исключений (owner, expiry, compensating controls)
```

---

## Example 2 — Fast incident-mode scan focused on exploitability

**EN:**
```
/security-scan

Context: actively exploited CVE announced in a transitive dependency
Timebox: 90 minutes
Scope:
  - Dependency path tracing to affected services
  - Runtime reachability confirmation
  - Exposure check for internet-facing routes
Output:
  - List of impacted services sorted by exploitability risk
  - Immediate mitigations (feature flags, traffic isolation, WAF rules)
  - Patch and rollback plan
```

**RU:**
```
/security-scan

Контекст: опубликован активно эксплуатируемый CVE в транзитивной зависимости
Таймбокс: 90 минут
Скоуп:
  - Трассировка dependency path до затронутых сервисов
  - Подтверждение runtime reachability
  - Проверка экспозиции интернет-facing маршрутов
Результат:
  - Список затронутых сервисов, отсортированный по риску exploitability
  - Немедленные mitigation-шаги (feature flags, изоляция трафика, WAF rules)
  - План патча и отката
```
