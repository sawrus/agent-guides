---
workflow: drift-check
---

# Prompt: `/drift-check`

Use when: detecting infrastructure drift — differences between IaC state and actual cloud resources — and deciding whether to remediate or update state.

---

## Example 1 — Scheduled drift audit

**EN:**
```
/drift-check

Environment: production (AWS eu-west-1)
IaC tool: Terraform
State location: s3://tf-state-myapp/envs/prod/terraform.tfstate
Scope: full — all modules (network, compute, database, IAM, monitoring)
Command: terraform plan -detailed-exitcode (exit 2 = drift detected)
Expected drift (known manual changes to accept):
  - RDS instance class bumped from db.t3.large to db.t3.xlarge last week (approved emergency change)
  - CloudWatch alarm threshold on order-service-latency adjusted manually
Classification needed:
  - ACCEPT: expected/approved manual changes → update tfvars to match
  - REMEDIATE: unauthorised changes → revert via terraform apply
  - INVESTIGATE: unknown changes → escalate to security review
Output: drift-report-2024-09-15.md with classified findings
```

**RU:**
```
/drift-check

Окружение: production (AWS eu-west-1)
Инструмент IaC: Terraform
Расположение state: s3://tf-state-myapp/envs/prod/terraform.tfstate
Скоуп: полный — все модули (network, compute, database, IAM, monitoring)
Команда: terraform plan -detailed-exitcode (exit 2 = обнаружен drift)
Ожидаемый drift (известные ручные изменения для принятия):
  - Класс RDS instance повышен с db.t3.large до db.t3.xlarge на прошлой неделе (одобренное экстренное изменение)
  - Порог CloudWatch alarm на order-service-latency скорректирован вручную
Необходимая классификация:
  - ПРИНЯТЬ: ожидаемые/одобренные ручные изменения → обновить tfvars чтобы соответствовало
  - ИСПРАВИТЬ: несанкционированные изменения → откатить через terraform apply
  - РАССЛЕДОВАТЬ: неизвестные изменения → эскалировать в security review
Результат: drift-report-2024-09-15.md с классифицированными находками
```

---

## Example 2 — Post-incident drift check

**EN:**
```
/drift-check

Trigger: post-incident INC-2024-088 — during incident response, engineer manually scaled EKS node group from 3 to 8 nodes; incident resolved but infra not reverted
Environment: production EKS cluster (eu-west-1)
Focus: EKS node groups, auto-scaling group desired counts
Expected: node count in Terraform = 3; actual = 8
Decision needed: scale back to 3 (traffic is back to normal) vs. update Terraform to 8 (if load justifies)
Load check: CloudWatch — current CPU < 40% on 8 nodes (3 nodes would be fine)
Action: scale back to 3 via Terraform, import new ASG config to state
```

**RU:**
```
/drift-check

Триггер: post-incident INC-2024-088 — во время реагирования на инцидент инженер вручную масштабировал EKS node group с 3 до 8 узлов; инцидент разрешён но инфра не откачена
Окружение: production EKS кластер (eu-west-1)
Фокус: EKS node groups, желаемые количества auto-scaling group
Ожидается: количество узлов в Terraform = 3; фактически = 8
Необходимое решение: уменьшить до 3 (трафик вернулся к норме) или обновить Terraform до 8 (если нагрузка оправдывает)
Проверка нагрузки: CloudWatch — текущий CPU < 40% на 8 узлах (3 узла было бы достаточно)
Действие: уменьшить до 3 через Terraform, импортировать новую конфигурацию ASG в state
```

---

## Example 3 — IAM permissions drift (security focus)

**EN:**
```
/drift-check

Scope: IAM only — detect permission creep in production AWS account
Tool: terraform plan scoped to iam/ module + AWS Config rules
Concern: 3 IAM roles had policies attached manually last month (not in Terraform)
Detection: compare Terraform state IAM attachments vs. AWS IAM actual attached policies
Risk classification: any admin-level policy attached outside Terraform = CRITICAL drift
Output: list of unexpected IAM changes with attached policy names; immediate remediation for CRITICAL
```

**RU:**
```
/drift-check

Скоуп: только IAM — обнаружить расширение прав в production AWS аккаунте
Инструмент: terraform plan с ограничением модуля iam/ + правила AWS Config
Озабоченность: к 3 IAM ролям были прикреплены политики вручную в прошлом месяце (не в Terraform)
Обнаружение: сравнить прикрепления IAM в Terraform state с фактически прикреплёнными политиками AWS IAM
Классификация рисков: любая политика уровня admin прикреплённая вне Terraform = КРИТИЧЕСКИЙ drift
Результат: список неожиданных изменений IAM с именами прикреплённых политик; немедленное исправление для КРИТИЧЕСКИХ
```
