---
workflow: onboard-repo
---

# Prompt: `/onboard-repo`

Use when: setting up CI/CD pipeline for a new repository from scratch.

---

## Example 1 — Python service on GitHub Actions

**EN:**
```
/onboard-repo

Repo: github.com/myorg/payment-service / Language: Python 3.12 / Framework: FastAPI
CI platform: GitHub Actions
Tests: pytest + coverage / Lint: ruff + mypy
Registry: ghcr.io (OIDC auth — no long-lived keys)
Deploy: Kubernetes (bare-metal, ArgoCD GitOps)
Environments: staging (auto on main merge) + production (manual approval, team-lead required)
Image signing: cosign + SBOM via Syft
Quality gates: coverage >= 80%, no Critical/High CVEs in Trivy scan
```

**RU:**
```
/onboard-repo

Репо: github.com/myorg/payment-service / Язык: Python 3.12 / Фреймворк: FastAPI
CI платформа: GitHub Actions
Тесты: pytest + coverage / Линтер: ruff + mypy
Реестр: ghcr.io (OIDC auth — без долгоживущих ключей)
Деплой: Kubernetes (bare-metal, ArgoCD GitOps)
Окружения: staging (авто при merge в main) + production (ручное подтверждение, team-lead)
Подпись образов: cosign + SBOM через Syft
Quality gates: coverage >= 80%, нет Critical/High CVE в Trivy scan
```

---

## Example 2 — Go service on self-hosted GitLab CI

**EN:**
```
/onboard-repo

Repo: gitlab.internal/backend/order-service / Language: Go 1.23
CI platform: GitLab CI (self-hosted, bare-metal runner tagged: [self-hosted, docker])
Tests: go test ./... / Lint: golangci-lint
Registry: registry.internal (authenticated, no OIDC — use GitLab CI_JOB_TOKEN)
Deploy: Helm to K8s staging namespace; production requires manual approval gate
Special: internal module proxy (GOPROXY=https://proxy.internal); runner has no public internet
SAST: GitLab built-in SAST template
```

**RU:**
```
/onboard-repo

Репо: gitlab.internal/backend/order-service / Язык: Go 1.23
CI платформа: GitLab CI (self-hosted, bare-metal runner с тегами: [self-hosted, docker])
Тесты: go test ./... / Линтер: golangci-lint
Реестр: registry.internal (аутентификация через CI_JOB_TOKEN, без OIDC)
Деплой: Helm в K8s staging namespace; production требует ручного подтверждения
Особенность: внутренний module proxy (GOPROXY=https://proxy.internal); runner без публичного интернета
SAST: встроенный GitLab SAST шаблон
```

---

## Example 3 — Quick: add missing security scan stage

**EN:**
```
/onboard-repo

Task: add Trivy container scan to existing GitHub Actions pipeline
Current stages: lint → test → build (already working)
Missing: image scan between build and deploy
Threshold: block on Critical/High; warn on Medium
Upload results to GitHub Security tab (SARIF format)
Platform: GitHub Actions / Image: ghcr.io/myorg/api:${{ github.sha }}
```

**RU:**
```
/onboard-repo

Задача: добавить Trivy сканирование контейнера в существующий GitHub Actions pipeline
Текущие стадии: lint → test → build (уже работают)
Отсутствует: сканирование образа между build и deploy
Порог: блокировать при Critical/High; предупреждать при Medium
Загрузить результаты в GitHub Security tab (формат SARIF)
Платформа: GitHub Actions / Образ: ghcr.io/myorg/api:${{ github.sha }}
```
