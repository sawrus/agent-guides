---
workflow: provision-env
---

# Prompt: `/provision-env`

Use when: provisioning a new environment (staging, preview, feature env) from Terraform/Helm configs with cost estimation and DNS/smoke validation.

---

## Example 1 — New staging environment

**EN:**
```
/provision-env

Environment name: staging-v2
Cloud: AWS (eu-west-1)
IaC tool: Terraform (modules in infra/terraform/envs/staging/)
Services to provision:
  - EKS cluster (t3.medium × 3 nodes, spot instances)
  - RDS PostgreSQL 16 (db.t3.medium, multi-AZ: false for staging)
  - ElastiCache Redis 7 (cache.t3.micro)
  - S3 bucket (staging-v2-assets) with versioning enabled
  - ALB + Route53 record: staging-v2.myapp.internal
Variable overrides vs. prod: smaller instance sizes; no multi-AZ; 7-day log retention
Cost estimate required: yes — alert if projected monthly > $800
DNS: staging-v2.myapp.com → ALB DNS (Route53 hosted zone: myapp.com)
Smoke test after provisioning: curl https://staging-v2.myapp.com/health → 200
State backend: S3 bucket tf-state-myapp, key envs/staging-v2/terraform.tfstate
```

**RU:**
```
/provision-env

Имя окружения: staging-v2
Облако: AWS (eu-west-1)
Инструмент IaC: Terraform (модули в infra/terraform/envs/staging/)
Сервисы для развёртывания:
  - EKS кластер (t3.medium × 3 узла, spot instances)
  - RDS PostgreSQL 16 (db.t3.medium, multi-AZ: false для staging)
  - ElastiCache Redis 7 (cache.t3.micro)
  - S3 bucket (staging-v2-assets) с включённым версионированием
  - ALB + Route53 запись: staging-v2.myapp.internal
Переопределения переменных vs. prod: меньшие размеры instance; без multi-AZ; хранение логов 7 дней
Оценка стоимости обязательна: да — предупреждать если прогнозируемые затраты в месяц > $800
DNS: staging-v2.myapp.com → ALB DNS (Route53 hosted zone: myapp.com)
Smoke test после развёртывания: curl https://staging-v2.myapp.com/health → 200
State backend: S3 bucket tf-state-myapp, ключ envs/staging-v2/terraform.tfstate
```

---

## Example 2 — Feature preview environment (ephemeral)

**EN:**
```
/provision-env

Environment type: ephemeral feature preview (auto-destroy after PR merge)
PR: #312 "Add product recommendations"
Namespace: preview-pr-312 (Kubernetes namespace in shared staging cluster — not new cluster)
Services: order-service:pr-312, recommendation-service:pr-312 (new service)
Shared infra (reuse existing): PostgreSQL staging DB (separate schema: preview_pr312), Redis staging
Ingress: pr-312.preview.myapp.internal (internal only, no public DNS)
Seed data: run make seed-preview DB_SCHEMA=preview_pr312
Lifetime: auto-destroy when PR #312 is closed or merged (GitHub Actions workflow)
Cost: namespace only — no new cloud resources; ~$0 additional
```

**RU:**
```
/provision-env

Тип окружения: эфемерная feature preview (авто-уничтожение после мержа PR)
PR: #312 "Добавить рекомендации продуктов"
Namespace: preview-pr-312 (Kubernetes namespace в shared staging кластере — не новый кластер)
Сервисы: order-service:pr-312, recommendation-service:pr-312 (новый сервис)
Общая инфра (переиспользовать существующую): PostgreSQL staging БД (отдельная схема: preview_pr312), Redis staging
Ingress: pr-312.preview.myapp.internal (только внутренний, без публичного DNS)
Seed данные: запустить make seed-preview DB_SCHEMA=preview_pr312
Время жизни: авто-уничтожение когда PR #312 закрывается или мержится (GitHub Actions workflow)
Стоимость: только namespace — нет новых облачных ресурсов; ~$0 дополнительно
```

---

## Example 3 — Quick / DR environment verification

**EN:**
```
/provision-env

Purpose: disaster recovery drill — spin up DR environment in us-east-1 from prod snapshots
Source: RDS snapshot rds:prod-postgres-2024-09-15, S3 sync from prod-assets bucket
Target region: us-east-1 (DR region)
Validation: verify app boots and read queries work; write operations disabled (DR = read-only)
Time limit: DR environment must be ready within 2 hours (RTO target)
Destroy after: 4 hours (drill complete, document RTO achieved)
```

**RU:**
```
/provision-env

Назначение: учения по аварийному восстановлению — развернуть DR окружение в us-east-1 из prod снапшотов
Источник: RDS снапшот rds:prod-postgres-2024-09-15, S3 sync из bucket prod-assets
Целевой регион: us-east-1 (DR регион)
Валидация: убедиться что приложение запускается и read запросы работают; операции записи отключены (DR = read-only)
Ограничение времени: DR окружение должно быть готово в течение 2 часов (цель RTO)
Уничтожить после: 4 часа (учения завершены, задокументировать достигнутый RTO)
```
