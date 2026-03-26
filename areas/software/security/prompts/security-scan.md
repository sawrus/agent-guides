---
workflow: security-scan
---

# Prompt: `/security-scan`

Use when: running a full automated security sweep — SAST, dependency audit, secrets detection, IaC checks — before a release or after a major change.

---

## Example 1 — Pre-release security gate

**EN:**
```
/security-scan

Trigger: release candidate v2.5.0 ready for staging sign-off
Scope: full — SAST + dependency CVEs + secrets + IaC (Terraform)
Stack: Python 3.12 / FastAPI, PostgreSQL, Redis, Terraform (AWS)
Tools available: bandit, ruff, safety, trufflehog, tfsec, semgrep
Severity threshold: block release on any Critical or High; report Medium/Low
Output: security-scan-report.md with findings, severity, remediation steps
Branch: release/2.5.0
```

**RU:**
```
/security-scan

Триггер: release candidate v2.5.0 готов к sign-off на staging
Скоуп: полный — SAST + CVE зависимостей + секреты + IaC (Terraform)
Стек: Python 3.12 / FastAPI, PostgreSQL, Redis, Terraform (AWS)
Доступные инструменты: bandit, ruff, safety, trufflehog, tfsec, semgrep
Порог серьёзности: блокировать релиз на любом Critical или High; отчитываться о Medium/Low
Результат: security-scan-report.md с находками, серьёзностью, шагами устранения
Ветка: release/2.5.0
```

---

## Example 2 — Post-incident targeted scan

**EN:**
```
/security-scan

Trigger: post-incident — suspected SQL injection in orders module (INC-2024-088)
Scope: targeted — SAST only on src/api/ and src/repositories/; dependency audit for SQLAlchemy
Priority: SQL injection patterns, unsanitised inputs, ORM bypass risks
Skip: IaC scan, secrets scan (already clean, saves time)
Output: findings with code location + PoC query if reproducible
Timeframe: results needed within 2 hours for incident postmortem
```

**RU:**
```
/security-scan

Триггер: после инцидента — подозрение на SQL injection в модуле orders (INC-2024-088)
Скоуп: целевой — только SAST на src/api/ и src/repositories/; аудит зависимостей для SQLAlchemy
Приоритет: паттерны SQL injection, неэкранированные входные данные, риски обхода ORM
Пропустить: IaC сканирование, проверку секретов (уже чисто, экономия времени)
Результат: находки с расположением кода + PoC запрос если воспроизводимо
Срок: результаты нужны в течение 2 часов для postmortem инцидента
```

---

## Example 3 — Dependency-only quick scan

**EN:**
```
/security-scan

Scope: dependency CVE audit only
Stack: Node.js 20 / Express, npm lockfile
Command: npm audit --audit-level=high
Auto-fix: apply non-breaking patches automatically (npm audit fix)
Report: list packages with unresolved High/Critical CVEs that need manual review
```

**RU:**
```
/security-scan

Скоуп: только аудит CVE зависимостей
Стек: Node.js 20 / Express, npm lockfile
Команда: npm audit --audit-level=high
Авто-исправление: применить неломающие патчи автоматически (npm audit fix)
Отчёт: список пакетов с неустранёнными High/Critical CVE которые требуют ручного ревью
```
