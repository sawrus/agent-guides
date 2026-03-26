---
workflow: security-scan-pipeline
---

# Prompt: `/security-scan-pipeline`

Use when: running a release-blocking security scan pipeline or remediating findings across secrets, containers, dependencies, and SBOM/signing controls.

---

## Example 1 — Full pre-release security scan

**EN:**
```
/security-scan-pipeline

Service: payment-service / Version: v2.5.0
Scope: full scan (code, dependencies, image, IaC)
Pipeline stage: pre-release gate
Scans to run:
  1. SAST: semgrep (ruleset: python, owasp) on src/
  2. Dependency CVE: trivy fs . (CRITICAL+HIGH block)
  3. Secrets: trufflehog git --since-commit HEAD~10
  4. Image: trivy image registry.internal/payment-service:v2.5.0 (CRITICAL+HIGH block)
  5. IaC: tfsec terraform/ (CRITICAL+HIGH block)
  6. SBOM: generate CycloneDX from image; attach via cosign
Expected output: pass/fail per scan + finding summary + exceptions list
Block release if: any unresolved Critical/High without approved exception
```

**RU:**
```
/security-scan-pipeline

Сервис: payment-service / Версия: v2.5.0
Скоуп: полное сканирование (код, зависимости, образ, IaC)
Стадия pipeline: pre-release gate
Сканирования:
  1. SAST: semgrep (ruleset: python, owasp) на src/
  2. CVE зависимостей: trivy fs . (CRITICAL+HIGH блокируют)
  3. Секреты: trufflehog git --since-commit HEAD~10
  4. Образ: trivy image registry.internal/payment-service:v2.5.0 (CRITICAL+HIGH блокируют)
  5. IaC: tfsec terraform/ (CRITICAL+HIGH блокируют)
  6. SBOM: генерация CycloneDX из образа; прикрепление через cosign
Ожидаемый результат: pass/fail по каждому скану + сводка находок + список исключений
Блокировать релиз если: есть неразрешённые Critical/High без утверждённого исключения
```

---

## Example 2 — Harden existing Python service Dockerfile

**EN:**
```
/security-scan-pipeline

Service: notification-service / Language: Python 3.12 + FastAPI
Current Dockerfile issues (from Trivy + OPA scan):
  - Runs as root (no USER instruction)
  - Base image: python:3.12 (full, not slim; 800MB with dev tools)
  - No multi-stage (test deps included in production image)
  - Base image tag not pinned to digest
  - COPY . . copies .env and .git into image
Hardening targets:
  1. Distroless or python:3.12-slim@sha256:<digest> base (< 150MB final)
  2. Non-root user (UID 1000)
  3. Multi-stage: builder with pip install; runtime with only app + deps
  4. .dockerignore: exclude .env, .git, tests/, __pycache__, *.pyc
  5. readOnlyRootFilesystem: true in K8s (mount emptyDir for /tmp)
  6. drop ALL capabilities; no privilege escalation
Show: before/after Dockerfile + Helm values securityContext patch
```

**RU:**
```
/security-scan-pipeline

Сервис: notification-service / Язык: Python 3.12 + FastAPI
Текущие проблемы Dockerfile (из Trivy + OPA скана):
  - Запуск от root (нет инструкции USER)
  - Base image: python:3.12 (полный, не slim; 800MB с dev tools)
  - Нет multi-stage (зависимости для тестов включены в production образ)
  - Тег base image не закреплён с digest
  - COPY . . копирует .env и .git в образ
Цели hardening:
  1. Distroless или python:3.12-slim@sha256:<digest> база (финальный < 150MB)
  2. Не-root пользователь (UID 1000)
  3. Multi-stage: builder с pip install; runtime только с приложением + зависимостями
  4. .dockerignore: исключить .env, .git, tests/, __pycache__, *.pyc
  5. readOnlyRootFilesystem: true в K8s (монтировать emptyDir для /tmp)
  6. drop ALL capabilities; без повышения привилегий
Показать: Dockerfile до/после + патч securityContext в Helm values
```

---

## Example 3 — Add SBOM + cosign to existing pipeline

**EN:**
```
/security-scan-pipeline

Service: payment-service / CI: GitHub Actions
Image: ghcr.io/myorg/payment-service:${{ github.sha }}
Current state: image built and pushed; no SBOM, no signature
Add to pipeline (after image push step):
  1. Generate SBOM in CycloneDX format using Syft
  2. Attach SBOM to image in OCI registry using cosign attach sbom
  3. Sign image with cosign using GitHub OIDC (keyless — no private key management)
  4. Generate SLSA provenance attestation (via docker/build-push-action provenance:true)
  5. Add verification step in deploy job: cosign verify before helm upgrade
  6. Store SBOM as build artifact (for audit/compliance download)
Show: complete GitHub Actions steps to insert after existing push step
```

**RU:**
```
/security-scan-pipeline

Сервис: payment-service / CI: GitHub Actions
Образ: ghcr.io/myorg/payment-service:${{ github.sha }}
Текущее состояние: образ собирается и пушится; без SBOM, без подписи
Добавить в pipeline (после шага push образа):
  1. Генерация SBOM в формате CycloneDX через Syft
  2. Прикрепление SBOM к образу в OCI registry через cosign attach sbom
  3. Подпись образа через cosign с GitHub OIDC (keyless — без управления приватным ключом)
  4. Генерация SLSA provenance attestation (через docker/build-push-action provenance:true)
  5. Добавить шаг верификации в deploy job: cosign verify перед helm upgrade
  6. Сохранить SBOM как build artifact (для загрузки при аудите/compliance)
Показать: полные шаги GitHub Actions для вставки после существующего шага push
```
