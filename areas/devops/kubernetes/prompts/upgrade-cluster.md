---
workflow: upgrade-cluster
---

# Prompt: `/upgrade-cluster`

Use when: upgrading Kubernetes control plane and worker nodes to a new minor or patch version.

---

## Example 1 — Minor version upgrade (production, zero downtime)

**EN:**
```
/upgrade-cluster

Cluster: prod-cluster-01 / Current: 1.29.8 / Target: 1.30.4
Nodes: 3 control plane (cp-01/02/03) + 6 workers (worker-01..06)
Constraints: zero downtime, upgrade window Sat 02:00–06:00 UTC
Staging: already on 1.30.4, healthy 72h
Pre-checks: kubent deprecated API scan, ArgoCD/cert-manager/ingress-nginx compat check, etcd backup
Rollback plan: required in upgrade PR before merge
```

**RU:**
```
/upgrade-cluster

Кластер: prod-cluster-01 / Текущая: 1.29.8 / Целевая: 1.30.4
Ноды: 3 control plane (cp-01/02/03) + 6 workers (worker-01..06)
Ограничения: zero downtime, окно обновления сб 02:00–06:00 UTC
Staging: уже на 1.30.4, стабильно 72ч
Пред-проверки: сканирование deprecated API через kubent, проверка совместимости ArgoCD/cert-manager/ingress-nginx, бэкап etcd
План отката: обязателен в PR до merge
```

---

## Example 2 — Security patch (fast-track, staging)

**EN:**
```
/upgrade-cluster

Cluster: staging-cluster-01 / Current: 1.30.2 / Target: 1.30.4
Reason: CVE-2024-XXXXX security patch — apply within 48h per policy
Nodes: 1 control plane + 3 workers
Staging: downtime < 5 min acceptable
Required: etcd backup + verify, control plane upgrade, rolling node upgrade
Skip: full 48h staging validation (this IS the staging cluster)
```

**RU:**
```
/upgrade-cluster

Кластер: staging-cluster-01 / Текущая: 1.30.2 / Целевая: 1.30.4
Причина: патч безопасности CVE-2024-XXXXX — применить в течение 48ч согласно политике
Ноды: 1 control plane + 3 workers
Staging: простой < 5 мин допустим
Требуется: бэкап etcd + верификация, обновление control plane, rolling обновление нод
Пропустить: полную 48ч валидацию staging (это и есть staging кластер)
```
