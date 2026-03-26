---
workflow: release-pipeline
---

# Prompt: `/release-pipeline`

Use when: designing or running a production release pipeline with versioning, supply-chain controls, and deployment gates.

---

## Example 1 — Semantic versioning + automated changelog

**EN:**
```
/release-pipeline

Repo: github.com/myorg/api-service
Release strategy: semantic versioning (semver) via git tags
Changelog: auto-generated from conventional commits (feat/fix/breaking)
Trigger: manual tag push (v1.2.3) → full release pipeline
Pipeline steps:
  1. Validate: all CI gates pass on tagged commit
  2. Build: image with tag=v1.2.3 AND digest; push to ghcr.io
  3. Sign: cosign sign + SBOM attach
  4. Release: GitHub Release with changelog + image digest in description
  5. Deploy staging: Helm upgrade --set image.tag=v1.2.3 --atomic
  6. Smoke test staging: automated; gate before production
  7. Deploy production: manual approval; canary 10% → 100%
```

**RU:**
```
/release-pipeline

Репо: github.com/myorg/api-service
Стратегия релизов: semantic versioning (semver) через git теги
Changelog: авто-генерация из conventional commits (feat/fix/breaking)
Триггер: ручной push тега (v1.2.3) → полный pipeline релиза
Шаги pipeline:
  1. Validate: все CI gates проходят на тегированном коммите
  2. Build: образ с tag=v1.2.3 И digest; push в ghcr.io
  3. Sign: cosign sign + SBOM attach
  4. Release: GitHub Release с changelog + image digest в описании
  5. Deploy staging: Helm upgrade --set image.tag=v1.2.3 --atomic
  6. Smoke test staging: автоматический; gate перед production
  7. Deploy production: ручное подтверждение; canary 10% → 100%
```

---

## Example 2 — Emergency hotfix release

**EN:**
```
/release-pipeline

Context: critical bug in v2.1.0 (CVE exploited in production); hotfix needed in < 2 hours
Branch: hotfix/cve-2024-payment from tag v2.1.0 (NOT from main — main has unreleased features)
Version: v2.1.1
Speed optimizations allowed:
  - Skip: integration tests (replace with targeted regression test for the fix)
  - Skip: changelog automation (write manually)
  - Keep: security scan (mandatory), smoke test (mandatory), canary deploy (mandatory)
Rollback plan: v2.1.0 image already in registry — Helm rollback in < 2 min if needed
```

**RU:**
```
/release-pipeline

Контекст: критический баг в v2.1.0 (CVE эксплуатируется в production); hotfix нужен за < 2 часа
Ветка: hotfix/cve-2024-payment от тега v2.1.0 (НЕ от main — там незарелиженные фичи)
Версия: v2.1.1
Допустимые оптимизации скорости:
  - Пропустить: интеграционные тесты (заменить целевым регрессионным тестом для исправления)
  - Пропустить: автоматизацию changelog (написать вручную)
  - Оставить: security scan (обязательно), smoke test (обязательно), canary deploy (обязательно)
План отката: образ v2.1.0 уже в реестре — Helm rollback за < 2 мин при необходимости
```

---

## Example 3 — Add full supply chain to existing pipeline

**EN:**
```
/release-pipeline

Service: checkout-service / CI: GitHub Actions
Current state: images built and pushed, no signing, no SBOM
Required:
  1. SBOM: generate CycloneDX SBOM with Syft during build; attach to image with cosign
  2. Signing: sign image with cosign using GitHub OIDC (keyless) after push
  3. Provenance: enable SLSA level 2 via docker/build-push-action (provenance: true)
  4. Verification: add cosign verify step in CD pipeline before every deploy
  5. Policy: Kyverno ClusterPolicy — block unsigned images in production namespace
  6. Dependency pinning: base image must reference @sha256 digest, not tag
Show full updated GitHub Actions workflow + Kyverno policy
```

**RU:**
```
/release-pipeline

Сервис: checkout-service / CI: GitHub Actions
Текущее состояние: образы собираются и пушатся, без подписи, без SBOM
Требуется:
  1. SBOM: генерация CycloneDX SBOM через Syft при сборке; прикрепление к образу через cosign
  2. Подпись: подпись образа через cosign с GitHub OIDC (keyless) после push
  3. Provenance: SLSA level 2 через docker/build-push-action (provenance: true)
  4. Верификация: добавить шаг cosign verify в CD pipeline перед каждым деплоем
  5. Политика: Kyverno ClusterPolicy — блокировка неподписанных образов в production namespace
  6. Pinning зависимостей: base image должен ссылаться на @sha256 digest, не тег
Показать полный обновлённый workflow GitHub Actions + Kyverno политику
```
