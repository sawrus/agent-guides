---
workflow: module-development
---

# Prompt: `/module-development`

Use when: creating or refactoring a Terraform module for team-wide reuse.

---

## Example 1 — New cloud-agnostic K8s node pool module

**EN:**
```
/module-development

Module: k8s-node-pool
Purpose: provision worker nodes with uniform config (Hetzner primary, AWS secondary)
Inputs: node_count, instance_type, zone, k8s_version (label only), common_tags
Outputs: node IPs (list), SSH fingerprints
Constraints:
  - No provider config inside module
  - All sensitive outputs marked sensitive = true
  - validation{} blocks on all critical variables
  - example/ dir with both Hetzner + AWS usage
```

**RU:**
```
/module-development

Модуль: k8s-node-pool
Назначение: создание worker нод с единой конфигурацией (Hetzner основной, AWS вторичный)
Входные параметры: node_count, instance_type, zone, k8s_version (только лейбл), common_tags
Выходные данные: IP нод (list), SSH fingerprints
Ограничения:
  - Без конфигурации провайдера внутри модуля
  - Все sensitive выходные данные: sensitive = true
  - validation{} блоки для всех критических переменных
  - Директория example/ с примерами для Hetzner и AWS
```

---

## Example 2 — Refactor: extract reusable VPC module from monolith

**EN:**
```
/module-development

Task: extract VPC/subnet config from environments/production/main.tf into reusable module
Current state: all networking hardcoded in one file (3 AZs, specific CIDRs, specific tags)
Target: generic modules/vpc/ with variable inputs for CIDR, AZ count, tags
Safety: use moved{} blocks to prevent destroy+recreate during extraction
Must work for: AWS (VPC/subnets/IGW/NAT) and Hetzner (network/subnets)
Include: README.md with required vs optional variables, outputs, example usage
```

**RU:**
```
/module-development

Задача: извлечь конфигурацию VPC/подсетей из environments/production/main.tf в переиспользуемый модуль
Текущее состояние: вся сеть захардкожена в одном файле (3 AZ, конкретные CIDR, конкретные теги)
Цель: универсальный modules/vpc/ с переменными для CIDR, количества AZ, тегов
Безопасность: использовать блоки moved{} для предотвращения destroy+recreate при рефакторинге
Должен работать для: AWS (VPC/подсети/IGW/NAT) и Hetzner (network/подсети)
Включить: README.md с обязательными и опциональными переменными, outputs, примером использования
```
