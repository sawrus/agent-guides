# Kubernetes — guidance index

## What this area covers

Self-hosted and managed Kubernetes cluster operations: cluster bootstrap, workload onboarding, RBAC design, network policies, resource governance, upgrade management, and pod-level debugging.

## Inherited from devops area

- Infrastructure-as-Code immutability principle — no manual kubectl edits in production.
- Git-based change management — all manifests version-controlled.
- Incident response severity classification from `sre/` area.

## Kubernetes-specific constraints

- All workloads require resource requests and limits before admission.
- Network policies must be explicit — no implicit allow-all in non-development namespaces.
- RBAC follows least-privilege; no cluster-admin bindings without documented justification.
- Cluster upgrades follow the approved version-skew window; no skip-version upgrades.

## Spec map

```text
.agent/
├── rules/
│   ├── cluster-standards.md      ← node sizing, OS, CRI, CNI constraints
│   ├── workload-security.md      ← PSA levels, RBAC defaults, network policy baselines
│   ├── resource-governance.md    ← requests/limits, LimitRange, QoS class targets
│   └── upgrade-policy.md         ← version skew rules, upgrade cadence, pre-checks
├── skills/
│   ├── helm-charts/SKILL.md          ← chart authoring, values design, release management
│   ├── rbac-design/SKILL.md          ← role/binding patterns, least-privilege recipes
│   ├── network-policies/SKILL.md     ← ingress/egress policies, namespace isolation
│   ├── resource-tuning/SKILL.md      ← VPA/HPA, right-sizing, QoS optimization
│   ├── pod-troubleshooting/SKILL.md  ← crash loops, OOM, pending pods, exec debugging
│   └── cluster-operations/SKILL.md  ← etcd, control plane, node drain/cordon
├── workflows/
│   ├── onboard-service.md     ← /onboard-service
│   ├── upgrade-cluster.md     ← /upgrade-cluster
│   ├── debug-workload.md      ← /debug-workload
│   └── cluster-bootstrap.md  ← /cluster-bootstrap
└── prompts/
    └── *.md
```
