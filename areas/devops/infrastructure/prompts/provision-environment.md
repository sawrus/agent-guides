---
workflow: provision-environment
---

# Prompt: `/provision-environment`

Use when: provisioning or expanding infrastructure environments with Terraform and Ansible, while keeping cost, node configuration, and rollout safety explicit.

---

## Example 1 — Full staging environment on Hetzner

**EN:**
```
/provision-environment

Environment: staging / Cloud: Hetzner Cloud
Scope: all (network + compute + K8s-ready node config)
Resources:
  - Private network: 10.0.0.0/16
  - 1× cx31 control plane + 3× cx21 workers (Ubuntu 22.04)
  - Load balancer for K8s API (port 6443)
  - Firewall: deny-all inbound; allow SSH from jump-host IP only
IaC: Terraform for cloud resources, Ansible for OS config (K8s prereqs, containerd, kubeadm)
Outputs: server IPs to SSM; Ansible inventory file
Cost estimate: required in plan output
```

**RU:**
```
/provision-environment

Окружение: staging / Облако: Hetzner Cloud
Скоуп: всё (сеть + вычисления + конфигурация нод для K8s)
Ресурсы:
  - Приватная сеть: 10.0.0.0/16
  - 1× cx31 control plane + 3× cx21 workers (Ubuntu 22.04)
  - Load balancer для K8s API (порт 6443)
  - Firewall: deny-all входящий; разрешить SSH только с IP jump-host
IaC: Terraform для облачных ресурсов, Ansible для конфига ОС
Выходные данные: IP серверов в SSM; inventory файл для Ansible
Оценка стоимости: обязательна в выводе plan
```

---

## Example 2 — Ansible role for K8s node prerequisites

**EN:**
```
/provision-environment

Task: write idempotent Ansible role for K8s node prerequisites
Target OS: Ubuntu 22.04 LTS
Role name: k8s-prereqs
Tasks to cover:
  - Disable swap (permanent, survives reboot: /etc/fstab edit)
  - Load kernel modules: overlay, br_netfilter (persistent via /etc/modules-load.d)
  - Set sysctl params: net.bridge.bridge-nf-call-iptables=1, net.ipv4.ip_forward=1
  - Install containerd (from official apt repo, pin version)
  - Configure containerd: SystemdCgroup=true, correct config.toml
  - Install kubeadm, kubelet, kubectl (pinned to 1.31.x; apt-mark hold)
  - Restart containerd handler (only on config change)
Testing: molecule test scenario with Ubuntu 22.04 container
```

**RU:**
```
/provision-environment

Задача: написать идемпотентную Ansible роль для K8s node prerequisites
Целевая ОС: Ubuntu 22.04 LTS
Название роли: k8s-prereqs
Задачи для покрытия:
  - Отключение swap (постоянно, переживает перезагрузку: редактирование /etc/fstab)
  - Загрузка kernel modules: overlay, br_netfilter (постоянно через /etc/modules-load.d)
  - Установка sysctl параметров: net.bridge.bridge-nf-call-iptables=1, net.ipv4.ip_forward=1
  - Установка containerd (из официального apt репозитория, с pinned версией)
  - Конфигурация containerd: SystemdCgroup=true, корректный config.toml
  - Установка kubeadm, kubelet, kubectl (pinned to 1.31.x; apt-mark hold)
  - Handler перезапуска containerd (только при изменении конфига)
Тестирование: molecule test сценарий с Ubuntu 22.04 контейнером
```

---

## Example 3 — Monthly cloud cost audit (Hetzner + AWS)

**EN:**
```
/provision-environment

Scope: full infrastructure cost audit
Cloud providers: Hetzner (bare-metal K8s cluster) + AWS (S3, SES, Route53)
Monthly budget: €2,000 / actual last 3 months: €2,800 (+40% over budget)
Terraform state available: all resources tagged with Project, Environment, Owner
Goals:
  1. Identify top-5 most expensive resources
  2. Find unused resources: stopped VMs, unattached volumes, unused LBs, idle databases
  3. Right-size: find over-provisioned nodes (< 20% average CPU/memory utilization)
  4. Spot opportunities: which workloads could use spot/preemptible instances?
  5. Output: prioritized savings plan with estimated monthly savings per action
Tools available: infracost (for TF estimate), Prometheus for utilization metrics
```

**RU:**
```
/provision-environment

Скоуп: полный аудит затрат на инфраструктуру
Облачные провайдеры: Hetzner (bare-metal K8s кластер) + AWS (S3, SES, Route53)
Месячный бюджет: €2,000 / фактически последние 3 месяца: €2,800 (+40% сверх бюджета)
Terraform state доступен: все ресурсы тегированы Project, Environment, Owner
Цели:
  1. Определить топ-5 самых дорогих ресурсов
  2. Найти неиспользуемые ресурсы: остановленные ВМ, неподключённые диски, простаивающие LB и БД
  3. Right-size: найти избыточно выделенные ноды (< 20% среднего использования CPU/памяти)
  4. Spot возможности: какие workloads могут использовать spot/preemptible инстансы?
  5. Результат: приоритизированный план экономии с оценкой ежемесячной экономии на каждое действие
Доступные инструменты: infracost (для оценки TF), Prometheus для метрик использования
```
