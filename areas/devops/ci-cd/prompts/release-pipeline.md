---
workflow: release-pipeline
---

# Prompt: `/release-pipeline`

Use when: designing or executing a production release pipeline with strong supply-chain guarantees, safe database rollout, and progressive delivery controls.

---

## Example 1 — High-risk release with schema change + feature flags

**EN:**
```
/release-pipeline

Service: payments-api
Version: v3.8.0
Risk level: high
Change type:
  - New payment routing engine behind feature flag `routing_v2`
  - Database migration (expand phase only) adding nullable columns + backfill job
Requirements:
  1. Build immutable image digest and sign keylessly with cosign
  2. Generate SLSA provenance + CycloneDX SBOM
  3. Verify identity-constrained signature and attestation before deploy
  4. Staging gate: 15 min soak + critical path integration tests
  5. Production canary: 5% (10m) -> 25% (15m) -> 50% (15m) -> 100%
  6. Rollback criteria:
     - 5xx > 1% for 5 min
     - p99 latency > 20% regression for 10 min
     - fast burn-rate alert fires
  7. Feature flag rollout by cohorts after service-level stability
Output:
  - Full CI/CD workflow YAML
  - Migration safety checklist
  - Rollback runbook
```

**RU:**
```
/release-pipeline

Сервис: payments-api
Версия: v3.8.0
Уровень риска: high
Тип изменений:
  - Новый роутинг платежей под feature flag `routing_v2`
  - Миграция БД (только expand-фаза): новые nullable-колонки + backfill job
Требования:
  1. Собрать immutable digest и подписать keyless через cosign
  2. Сгенерировать SLSA provenance + CycloneDX SBOM
  3. Выполнить verify подписи/attestation с identity constraints перед деплоем
  4. Staging gate: 15 минут наблюдения + интеграционные критичные тесты
  5. Canary в production: 5% (10м) -> 25% (15м) -> 50% (15м) -> 100%
  6. Критерии отката:
     - 5xx > 1% в течение 5 минут
     - p99 latency хуже baseline на >20% в течение 10 минут
     - сработал fast burn-rate alert
  7. Раскатка feature flag по когортам после стабилизации сервиса
Результат:
  - Полный CI/CD workflow YAML
  - Чеклист безопасности миграции
  - Runbook отката
```

---

## Example 2 — Compliance-grade supply chain hardening

**EN:**
```
/release-pipeline

Context: move existing GitHub Actions pipeline to compliance-grade release controls
Current state: tests + image build only
Target:
  - OIDC federation for cloud auth (remove static secrets)
  - Keyless cosign signing of container digest
  - SLSA provenance attestation generation and verification
  - SBOM attach and retention policy >= 1 year
  - Admission policy in production namespace: signed + attested + digest-only images
Provide:
  - Updated release workflow
  - Example Kyverno/Gatekeeper policies
  - Failure-mode behavior (fail closed)
```

**RU:**
```
/release-pipeline

Контекст: перевести существующий GitHub Actions pipeline на compliance-grade контроль релизов
Текущее состояние: только тесты + сборка образа
Цель:
  - OIDC federation для cloud auth (убрать static secrets)
  - Keyless cosign-подпись digest контейнера
  - Генерация и проверка SLSA provenance attestation
  - Прикрепление SBOM и политика хранения >= 1 года
  - Admission policy в production: только signed + attested + digest-only образы
Нужно выдать:
  - Обновлённый workflow релиза
  - Примеры политик Kyverno/Gatekeeper
  - Поведение при сбоях (fail closed)
```
