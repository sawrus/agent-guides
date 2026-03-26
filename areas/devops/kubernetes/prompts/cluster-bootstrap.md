---
workflow: cluster-bootstrap
---

# Prompt: `/cluster-bootstrap`

Use when: provisioning a new self-hosted Kubernetes cluster from bare-metal.

---

## Example 1 — Production HA cluster (kubeadm)

**EN:**
```
/cluster-bootstrap

Cluster: prod-cluster-eu
Nodes: CP [cp-01/02/03: 192.168.10.10-12], Workers [w-01..06: 192.168.10.20-25]
HA VIP: 192.168.10.5 (keepalived + haproxy)
OS: Ubuntu 22.04 LTS / K8s: 1.31.x
Pod CIDR: 10.244.0.0/16 / Service CIDR: 10.96.0.0/12
CNI: Cilium + Hubble / Storage: Longhorn / LB: MetalLB (pool: .100-.150)
Core add-ons: ArgoCD, cert-manager, External Secrets → Vault, kube-prometheus-stack, OPA Gatekeeper
Security: etcd encryption at rest (AES-CBC), PSA restricted on production namespaces
```

**RU:**
```
/cluster-bootstrap

Кластер: prod-cluster-eu
Ноды: CP [cp-01/02/03: 192.168.10.10-12], Workers [w-01..06: 192.168.10.20-25]
HA VIP: 192.168.10.5 (keepalived + haproxy)
ОС: Ubuntu 22.04 LTS / K8s: 1.31.x
Pod CIDR: 10.244.0.0/16 / Service CIDR: 10.96.0.0/12
CNI: Cilium + Hubble / Хранилище: Longhorn / LB: MetalLB (pool: .100-.150)
Основные компоненты: ArgoCD, cert-manager, External Secrets → Vault, kube-prometheus-stack, OPA Gatekeeper
Безопасность: шифрование etcd at rest (AES-CBC), PSA restricted в production namespaces
```

---

## Example 2 — Lightweight lab cluster (k3s)

**EN:**
```
/cluster-bootstrap

Cluster: lab-01 / Distribution: k3s
Nodes: [lab-01: 192.168.1.10 server+agent, lab-02/03: 192.168.1.11-12 agents]
OS: Rocky Linux 9 / K8s: latest k3s stable
CNI: Flannel (default) / Storage: local-path / LB: none (port-forward)
Required: kubeconfig on workstation, helm + kubectl configured
Skip: HA, etcd encryption, OPA policies, PDB (lab environment)
```

**RU:**
```
/cluster-bootstrap

Кластер: lab-01 / Дистрибутив: k3s
Ноды: [lab-01: 192.168.1.10 server+agent, lab-02/03: 192.168.1.11-12 agents]
ОС: Rocky Linux 9 / K8s: последний стабильный k3s
CNI: Flannel (по умолчанию) / Хранилище: local-path / LB: нет (port-forward)
Требуется: kubeconfig на рабочей станции, настроены helm + kubectl
Пропустить: HA, шифрование etcd, OPA политики, PDB (lab окружение)
```
