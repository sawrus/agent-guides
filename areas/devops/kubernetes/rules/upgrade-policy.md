---
description: Version skew limits, cadence, pre-checks, and order for Kubernetes cluster upgrades.
trigger: manual
---

# Cluster upgrade policy

- Keep production clusters within 2 minor versions of the latest stable Kubernetes release.
- Apply patch versions to every cluster within 30 days of release.
- Upgrade one minor version at a time; never skip a minor version.
- Upgrade dev and staging first; upgrade production within 60 days after the staging upgrade passed.
- Keep nodes at most 2 minor versions behind the control plane, and never run `kubelet` newer than `kube-apiserver`.
- Keep `kubectl` within one minor version of the server.
- Check that cert-manager, the ingress controller, the CNI, and the GitOps controller list the target version as supported before the upgrade.
- Run `kubent` or `pluto detect-all-in-cluster` and remove every deprecated API before the upgrade.
- Take and verify an etcd snapshot within 1 hour before a self-managed control plane upgrade.
- Check that every node is `Ready` and that no `PodDisruptionBudget` blocks a drain (`ALLOWED DISRUPTIONS` above 0).
- Do not start an upgrade during an open P0 or P1 incident.
- Upgrade the control plane before the nodes, one control plane node at a time.
- Upgrade worker nodes with `kubectl cordon`, `kubectl drain --ignore-daemonsets --delete-emptydir-data`, upgrade, and `kubectl uncordon`.
- Write the rollback steps (etcd snapshot restore, previous node image) in the upgrade merge request before you start.
