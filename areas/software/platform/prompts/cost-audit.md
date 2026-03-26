---
workflow: cost-audit
---

# Prompt: `/cost-audit`

Use when: auditing cloud spend, finding waste, and producing an optimisation plan with ROI estimates.

---

## Example 1 — Monthly cost review

**EN:**
```
/cost-audit

Cloud: AWS (all services, eu-west-1 + us-east-1)
Period: August 2024
Current monthly spend: $18 400 (budget: $15 000 — 23% over)
Data source: AWS Cost Explorer export (cost-explorer-aug-2024.csv attached)
Top cost drivers (from Cost Explorer):
  - EC2/EKS: $9 200 (50%)
  - RDS: $3 100 (17%)
  - Data transfer: $2 800 (15%)
  - ElastiCache: $1 400 (8%)
  - Other: $1 900 (10%)
Focus areas: EC2 rightsizing, data transfer optimisation, identify idle/orphaned resources
Output: cost-audit-aug-2024.md — waste findings, savings estimate per fix, effort level (easy/medium/hard)
```

**RU:**
```
/cost-audit

Облако: AWS (все сервисы, eu-west-1 + us-east-1)
Период: август 2024
Текущие ежемесячные расходы: $18 400 (бюджет: $15 000 — превышение на 23%)
Источник данных: экспорт AWS Cost Explorer (cost-explorer-aug-2024.csv приложен)
Главные статьи затрат (из Cost Explorer):
  - EC2/EKS: $9 200 (50%)
  - RDS: $3 100 (17%)
  - Передача данных: $2 800 (15%)
  - ElastiCache: $1 400 (8%)
  - Остальное: $1 900 (10%)
Области фокуса: rightsizing EC2, оптимизация передачи данных, выявление простаивающих/заброшенных ресурсов
Результат: cost-audit-aug-2024.md — находки по расточительству, оценка экономии на каждое исправление, уровень усилий (лёгкий/средний/тяжёлый)
```

---

## Example 2 — Targeted EC2 rightsizing

**EN:**
```
/cost-audit

Scope: EC2 and EKS node groups only
Environment: production + staging
Data: AWS Compute Optimizer recommendations (export attached) + CloudWatch CPU/memory metrics (last 30 days)
Current cluster: 3 × m5.2xlarge (8 vCPU, 32 GB) — avg CPU 18%, avg memory 34%
Hypothesis: overprovisioned by 50%; could downsize to m5.xlarge (4 vCPU, 16 GB)
Savings estimate: m5.2xlarge $0.384/hr → m5.xlarge $0.192/hr × 3 nodes × 720hr = $415/mo
Risk: memory spikes during peak (check p99 memory); CPU burst capacity
Output: rightsizing recommendation with p99 metrics evidence + migration plan (rolling node replacement)
```

**RU:**
```
/cost-audit

Скоуп: только EC2 и EKS node groups
Окружение: production + staging
Данные: рекомендации AWS Compute Optimizer (экспорт приложен) + метрики CPU/memory CloudWatch (последние 30 дней)
Текущий кластер: 3 × m5.2xlarge (8 vCPU, 32 GB) — средний CPU 18%, средняя память 34%
Гипотеза: избыточное обеспечение на 50%; можно уменьшить до m5.xlarge (4 vCPU, 16 GB)
Оценка экономии: m5.2xlarge $0.384/ч → m5.xlarge $0.192/ч × 3 узла × 720ч = $415/мес
Риск: всплески памяти в часы пик (проверить p99 память); пиковая пропускная способность CPU
Результат: рекомендация по rightsizing с доказательствами метрик p99 + план миграции (поочерёдная замена узлов)
```

---

## Example 3 — Orphaned resources cleanup

**EN:**
```
/cost-audit

Scope: find and clean up orphaned/idle resources
Cloud: AWS eu-west-1
Check for:
  - Unattached EBS volumes (> 7 days unattached)
  - Unused Elastic IPs (not associated with running instance)
  - Old snapshots (> 90 days, not referenced in Terraform)
  - Stopped EC2 instances (> 14 days stopped, not scheduled)
  - Empty/unused S3 buckets
Tool: use AWS CLI + boto3 script to enumerate; cross-reference Terraform state
Output: deletion candidate list with last-used date and monthly cost per resource
Approval: list for human review before deletion — do not auto-delete
```

**RU:**
```
/cost-audit

Скоуп: найти и очистить заброшенные/простаивающие ресурсы
Облако: AWS eu-west-1
Проверить:
  - Не прикреплённые EBS тома (> 7 дней без прикрепления)
  - Неиспользуемые Elastic IP (не связаны с работающим instance)
  - Старые снапшоты (> 90 дней, не используются в Terraform)
  - Остановленные EC2 instances (> 14 дней остановлены, не по расписанию)
  - Пустые/неиспользуемые S3 bucket
Инструмент: использовать AWS CLI + boto3 скрипт для перечисления; сверить с Terraform state
Результат: список кандидатов на удаление с датой последнего использования и ежемесячной стоимостью за ресурс
Одобрение: список для ручного ревью перед удалением — не удалять автоматически
```
