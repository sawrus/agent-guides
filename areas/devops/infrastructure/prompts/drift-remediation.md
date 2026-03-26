---
workflow: drift-remediation
---

# Prompt: `/drift-remediation`

Use when: detecting and remediating infrastructure drift between Terraform state and actual cloud resources.

---

## Example 1 — Scheduled weekly drift audit

**EN:**
```
/drift-remediation

Environment: production
Scope: all Terraform components (vpc, k8s-nodes, rds, iam-roles)
Mode: detect + classify (do NOT apply automatically)
Output:
  - Drifted resources with change type (add/change/destroy)
  - Classification: ACCEPT / REMEDIATE / INVESTIGATE per finding
  - IAM or security group drift → automatic INVESTIGATE + incident
  - Cost impact of untracked resources
```

**RU:**
```
/drift-remediation

Окружение: production
Скоуп: все Terraform компоненты (vpc, k8s-nodes, rds, iam-roles)
Режим: обнаружение + классификация (НЕ применять автоматически)
Вывод:
  - Ресурсы с отклонением и типом изменения (add/change/destroy)
  - Классификация: ACCEPT / REMEDIATE / INVESTIGATE для каждой находки
  - Отклонение IAM или security group → автоматически INVESTIGATE + инцидент
  - Влияние на стоимость неотслеживаемых ресурсов
```

---

## Example 2 — Post-incident: codify manual change

**EN:**
```
/drift-remediation

Context: INC-2024-099 — RDS manually scaled during P1 (db.r6g.large → db.r6g.xlarge)
Environment: production / Component: rds-postgres only
Decision: keep larger instance; codify in Terraform
Task:
  1. Confirm drift = only instance class change
  2. Update terraform.tfvars: db_instance_class = "db.r6g.xlarge"
  3. Run plan — must show 0 changes (no-op = codified)
  4. Merge PR; close incident
```

**RU:**
```
/drift-remediation

Контекст: INC-2024-099 — RDS вручную масштабирован во время P1 (db.r6g.large → db.r6g.xlarge)
Окружение: production / Компонент: только rds-postgres
Решение: оставить более крупный инстанс; закодировать в Terraform
Задача:
  1. Подтвердить что отклонение = только изменение класса инстанса
  2. Обновить terraform.tfvars: db_instance_class = "db.r6g.xlarge"
  3. Запустить plan — должен показать 0 изменений (no-op = закодировано)
  4. Слить PR; закрыть инцидент
```
