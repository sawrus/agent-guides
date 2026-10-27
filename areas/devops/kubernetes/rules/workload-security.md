---
description: Pod security, service accounts, RBAC, network policies, and secrets for Kubernetes workloads.
paths:
  - "**/k8s/**"
  - "**/kubernetes/**"
  - "**/manifests/**"
  - "**/charts/**"
  - "**/kustomization.yaml"
  - "**/rbac/**"
---

# Workload security

- Label production namespaces `pod-security.kubernetes.io/enforce: restricted` and staging namespaces `enforce: baseline`.
- Set `runAsNonRoot: true`, a non-zero `runAsUser`, `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, `capabilities.drop: ["ALL"]`, and `seccompProfile.type: RuntimeDefault` on every container.
- Mount an `emptyDir` volume for paths the application writes, such as `/tmp`.
- Never set `privileged: true`, `hostNetwork`, `hostPID`, or `hostIPC` in a workload namespace.
- Create a dedicated `ServiceAccount` per workload; never use the `default` service account.
- Set `automountServiceAccountToken: false` unless the pod calls the Kubernetes API.
- Use a namespaced `Role` and `RoleBinding`; use a `ClusterRole` only for cross-namespace access and document the reason in an annotation.
- Never bind `cluster-admin` or the `system:masters` group to an application identity.
- Do not use wildcard `*` in `verbs`, `resources`, or `apiGroups` of a Role or ClusterRole.
- Check every new Role with `kubectl auth can-i --list --as=system:serviceaccount:<ns>:<sa>`.
- Add a `default-deny-all` NetworkPolicy (`podSelector: {}`, `policyTypes: [Ingress, Egress]`) to every namespace.
- Allow egress to DNS (UDP and TCP port 53 to `kube-dns`) explicitly in namespaces with default deny.
- Allow ingress per workload with `podSelector` and `namespaceSelector` on labels; do not allow `0.0.0.0/0` ingress to pods.
- Never put secrets in a `ConfigMap` or as literal `env` values; sync them with External Secrets Operator from a secret manager.
