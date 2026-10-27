---
name: debug-workload
type: workflow
trigger: /debug-workload
description: Diagnose a failing Kubernetes workload and fix it in the manifests or Helm values.
inputs:
  - workload
  - namespace
  - symptom
outputs:
  - root_cause
  - manifest_fix
selection:
  general: false
  use-when: "The request reports a pod in CrashLoopBackOff, Pending, ImagePullBackOff, OOMKilled, failing probes, or a Service with no endpoints in Kubernetes."
  avoid-when: "The application code has a bug that reproduces outside the cluster; use the debug workflow."
uses-skills:
  - pod-troubleshooting
  - helm-charts
related-rules:
  - resource-governance.md
  - workload-security.md
  - cluster-standards.md
checks:
  - helm lint <chart>
artifacts:
  - charts/<chart>/values*.yaml
---

# Debug a workload

Example request: payment-service is in CrashLoopBackOff every 30 seconds since the v2.3.1 deploy; find the cause and fix it.

## Steps

### 1. Read the state

- **Do:** confirm the kube context with the user. Run read-only commands: `kubectl get pods -o wide`,
  `kubectl describe pod <pod>`, `kubectl get events --sort-by=.lastTimestamp`, and
  `kubectl logs <pod> --previous`. Note the exit code, the reason, and the last good revision
  (`helm history <release>`).
- **Done when:** you can state the pod phase, the container reason, and the time it started.

### 2. Find the cause

- **Do:** follow the `pod-troubleshooting` skill for the reason you found. Compare the failing revision with the
  last good one: image digest, values, ConfigMap, Secret keys, resources, probes
  (`helm diff revision <release> <good> <bad>` or `git diff`).
- **Done when:** one change or limit explains the failure, backed by an event, a log line, or a metric.

### 3. Fix in source

- **Do:** change the chart values, manifest, or application config in the repository, not with `kubectl edit`.
  Render and lint it (`helm template`, `helm lint`, `kubectl apply --dry-run=server` against a non-production
  cluster). Ask the user first before any command that writes to a cluster.
- **Done when:** the rendered manifest contains the fix and `helm lint` passes.

### 4. Roll out and verify

- **Do:** ask the user first before `helm upgrade`, `kubectl rollout restart`, or a rollback. After the user
  runs or approves it, watch `kubectl rollout status` and the restarts count.
- **Done when:** all replicas are `Ready`, restarts stay at 0 for 10 minutes, and the docs page of the service
  notes the cause.
