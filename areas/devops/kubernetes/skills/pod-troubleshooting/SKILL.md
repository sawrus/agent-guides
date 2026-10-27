---
name: pod-troubleshooting
description: "Decision procedure to find why a Kubernetes pod is Pending, CrashLoopBackOff, OOMKilled, ImagePullBackOff, not Ready, or unreachable, with read-only kubectl commands. Use when a workload does not start or does not serve traffic."
---

# Pod troubleshooting

All commands in steps 1–4 are read-only. Confirm the context first: `kubectl config current-context`.

## 1. Get the state

```bash
kubectl get pods -n <ns> -l app=<name> -o wide
kubectl describe pod <pod> -n <ns>          # read Events at the bottom
kubectl get events -n <ns> --sort-by=.lastTimestamp | tail -20
```

## 2. Follow the status

- **Pending**
  - Event `Insufficient cpu/memory`: requests are larger than free node capacity. Compare with
    `kubectl describe nodes | grep -A5 Allocated`.
  - Event `didn't match node affinity/selector` or `untolerated taint`: check `nodeSelector`, `affinity`, and
    `tolerations`.
  - Event `unbound PersistentVolumeClaim`: `kubectl get pvc -n <ns>` and check the StorageClass.
- **ImagePullBackOff / ErrImagePull**
  - Check the image name and tag in the event. Check `imagePullSecrets` and that the registry allows the node.
- **CrashLoopBackOff**
  - Read the previous container log: `kubectl logs <pod> -n <ns> -c <container> --previous`.
  - Exit code `1` or a stack trace: an application error; read config and env with
    `kubectl get pod <pod> -n <ns> -o yaml`.
  - Missing ConfigMap or Secret key: the event says `couldn't find key`.
- **OOMKilled** (`Last State: Terminated, Reason: OOMKilled`)
  - Compare `kubectl top pod <pod> -n <ns>` with `resources.limits.memory`. For the JVM, check that
    `-XX:MaxRAMPercentage` fits the limit. For Go, check `GOMEMLIMIT`.
- **Running but not Ready**
  - Read the readiness probe in `describe`. Run the probe from inside:
    `kubectl exec <pod> -n <ns> -- wget -qO- localhost:<port><path>`.
- **Ready but unreachable**
  - `kubectl get endpointslices -n <ns> -l kubernetes.io/service-name=<svc>` must list the pod IPs.
  - Compare the Service `selector` and `targetPort` with the pod labels and container port.
  - Check NetworkPolicies in the namespace: `kubectl get networkpolicy -n <ns>`.
  - Test from a debug pod: `kubectl debug -n <ns> -it <pod> --image=busybox:1.36 -- wget -qO- <svc>:<port>`.

## 3. Check recent changes

```bash
kubectl rollout history deployment/<name> -n <ns>
kubectl diff -f <manifest-or-rendered-chart>
```

Compare the failing revision with the last working one. A change in image, env, or config is the first suspect.

## 4. Write down the cause

State the cause with the event, log line, or metric that proves it.

## 5. Fix

1. Fix the cause in the manifest, chart values, or application code, and ship it through the normal pipeline.
2. Ask the user first before any change in the cluster: `kubectl rollout undo`, `kubectl delete pod`,
   `kubectl scale`, `kubectl edit`, or `helm rollback`.
3. After the fix: `kubectl rollout status deployment/<name> -n <ns>` returns success.
