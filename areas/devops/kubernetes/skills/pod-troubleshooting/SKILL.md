---
name: pod-troubleshooting
type: skill
description: "Systematic diagnosis of Kubernetes pod failures — CrashLoopBackOff, OOMKilled, Pending, ImagePullBackOff, and service connectivity issues. Use when the user encounters pods not starting, container restart loops, scheduling failures, or service unreachability in a K8s cluster."
related-rules:
  - resource-governance.md
  - workload-security.md
allowed-tools: Read, Bash
---

# Skill: Pod Troubleshooting

> **Expertise:** Systematic K8s failure diagnosis — from symptom to root cause in under 10 commands.

## When to load

When a pod is not Running, a service is unreachable, or a deployment is stuck.

## Diagnostic Decision Tree

```
Pod not Running?
├── Status: Pending
│   ├── No nodes match → check node selectors, taints, resource requests
│   └── PVC not bound → check StorageClass, PV availability
├── Status: CrashLoopBackOff
│   ├── Exit code 0 → process exited cleanly but K8s restarts it → check command
│   ├── Exit code 1 → app error → check logs
│   ├── Exit code 137 → OOMKilled → increase memory limit
│   └── Exit code 143 → SIGTERM not handled → fix graceful shutdown
├── Status: ImagePullBackOff
│   ├── Image doesn't exist → check tag/digest
│   └── Registry auth fails → check imagePullSecret
└── Status: Error / Init:Error
    └── Init container failed → check init container logs
```

## Command Cheatsheet

```bash
# 1. Overview — what's wrong
kubectl get pods -n <ns> -o wide
kubectl describe pod <pod> -n <ns>          # events section is the first place to look

# 2. Logs
kubectl logs <pod> -n <ns>                  # current container
kubectl logs <pod> -n <ns> --previous       # last crashed container (CrashLoop)
kubectl logs <pod> -n <ns> -c <container>   # specific container in multi-container pod

# 3. Exec into running pod
kubectl exec -it <pod> -n <ns> -- /bin/sh

# 4. Resource pressure check
kubectl top nodes
kubectl top pods -n <ns>

# 5. Events (cluster-wide, sorted)
kubectl get events -n <ns> --sort-by='.lastTimestamp' | tail -20

# 6. Debug ephemeral container (no exec needed — distroless images)
kubectl debug -it <pod> -n <ns> --image=busybox:latest --target=<container>

# 7. Node-level debug
kubectl debug node/<node-name> -it --image=ubuntu
```

## CrashLoopBackOff Runbook

```bash
# Step 1: Get exit code
kubectl describe pod <pod> -n <ns> | grep -A5 "Last State:"

# Step 2: Get crash logs (may only appear in --previous)
kubectl logs <pod> -n <ns> --previous --tail=100

# Step 3: Check if OOMKilled
kubectl describe pod <pod> -n <ns> | grep -i "OOMKilled\|Reason:"
# If OOMKilled → increase memory limit or find memory leak

# Step 4: Check security context (common in restricted namespaces)
# Error: "permission denied" or "operation not permitted" → readOnlyRootFilesystem or dropped capabilities
```

## Pending Pod Runbook

```bash
# Check why pod can't be scheduled
kubectl describe pod <pod> -n <ns> | grep -A20 "Events:"

# Common causes:
# "Insufficient cpu/memory" → check node capacity and pod requests
kubectl describe nodes | grep -A5 "Allocated resources:"

# "node(s) had taints that the pod didn't tolerate"
kubectl get nodes -o custom-columns=NAME:.metadata.name,TAINTS:.spec.taints

# "0/3 nodes are available: 3 node(s) didn't match node affinity"
# → check pod nodeSelector / affinity vs node labels
kubectl get nodes --show-labels
```

## Service Connectivity Runbook

```bash
# Is the service selecting the right pods?
kubectl get endpoints <svc> -n <ns>       # should show pod IPs; empty = selector mismatch

# Test DNS resolution from within cluster
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup <svc>.<ns>.svc.cluster.local

# Test HTTP connectivity
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- curl -v http://<svc>.<ns>.svc.cluster.local:<port>/health

# Check NetworkPolicy blocking traffic
# Install Hubble CLI (Cilium) or use:
kubectl exec -n kube-system <cilium-pod> -- cilium monitor --from-pod <src-pod>
```

## OOMKilled Prevention

```bash
# Find actual peak memory usage via metrics
kubectl top pods -n <ns> --sort-by=memory

# Check Vertical Pod Autoscaler recommendation (if VPA installed)
kubectl describe vpa <name> -n <ns> | grep -A10 "Recommendation:"

# Rule of thumb: limit = 1.5× observed peak; request = 0.6× observed peak
```
