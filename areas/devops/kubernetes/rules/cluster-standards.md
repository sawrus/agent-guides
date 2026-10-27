---
description: Control plane, node, runtime, CNI, and exposure standards for Kubernetes clusters and their config.
paths:
  - "**/clusters/**"
  - "**/cluster/**"
  - "**/kubeadm*.yaml"
  - "**/talos/**"
  - "**/eks/**"
  - "**/gke/**"
---

# Cluster standards

- Run at least 3 control plane nodes across 3 failure domains in production; allow a single control plane node only in clusters labelled `env=dev`.
- Never schedule etcd on worker nodes.
- Use a managed control plane (EKS, GKE, AKS) or kubeadm, RKE2, k3s, or Talos for self-managed clusters.
- Use `containerd` as the container runtime; never use Docker Engine as the CRI.
- Keep the same OS image and kernel version within a node group.
- Add the labels `topology.kubernetes.io/zone`, `topology.kubernetes.io/region`, `node.kubernetes.io/instance-type`, and `environment` to every node.
- Use Cilium for new clusters; use Calico only for existing clusters; never use Flannel outside dev clusters.
- Choose pod and service CIDR ranges that do not overlap each other or the routed network.
- Expose production services through `Ingress`, `Gateway`, or `type: LoadBalancer`; do not use `NodePort` in production.
- Enable etcd encryption at rest with an `EncryptionConfiguration` that uses a KMS or `aescbc` provider.
- Enable API server audit logging and ship the audit log to central storage.
