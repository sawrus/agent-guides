---
description: Resource requests and limits, probes, autoscaling, disruption budgets, and quotas for Kubernetes workloads.
paths:
  - "**/k8s/**"
  - "**/kubernetes/**"
  - "**/manifests/**"
  - "**/charts/**"
  - "**/kustomization.yaml"
  - "**/values*.yaml"
---

# Resource governance

- Set `resources.requests.cpu`, `resources.requests.memory`, and `resources.limits.memory` for every container.
- Set `limits.memory` equal to `requests.memory` for stateful and tier 1 workloads (`Guaranteed` QoS for memory).
- Never deploy a `BestEffort` pod (no resources block) to a production namespace.
- Derive requests from observed usage: set CPU requests near the p95 of `container_cpu_usage_seconds_total` rate and memory requests near the p95 working set plus 20 %.
- Add `readinessProbe` and `livenessProbe` to every serving container; add `startupProbe` when start takes over 30 seconds.
- Do not point `livenessProbe` at an endpoint that checks downstream dependencies.
- Add a `HorizontalPodAutoscaler` with `minReplicas: 2` or more for tier 1 stateless workloads.
- Do not set a fixed `replicas` value in the manifest when an HPA manages the deployment.
- Add a `PodDisruptionBudget` with `minAvailable` or `maxUnavailable` for every workload with 2 or more replicas.
- Add `topologySpreadConstraints` on `topology.kubernetes.io/zone` with `maxSkew: 1` for tier 1 workloads.
- Add a `LimitRange` with default requests and limits to every production namespace.
- Add a `ResourceQuota` to every production namespace.
- Set `terminationGracePeriodSeconds` longer than the longest request timeout of the service.
