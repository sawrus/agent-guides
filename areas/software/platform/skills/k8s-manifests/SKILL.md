---
name: k8s-manifests
description: "Provides production Kubernetes deployment, HPA, and PodDisruptionBudget templates; use when writing Kubernetes YAML, designing Helm charts, setting resource limits, configuring probes, or reviewing pod security."
---

# Skill: Kubernetes Manifests & Helm

## When to load

When writing K8s YAML, designing Helm charts, setting resource limits, configuring probes, or reviewing pod security.

## Production Deployment Template

```yaml
spec:
  replicas: {{ .Values.replicaCount }}  # Min 2 for Tier 1
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
      terminationGracePeriodSeconds: 60
      containers:
        - name: api
          image: "{{ .Values.image.repository }}@{{ .Values.image.digest }}"
          resources:
            requests: { cpu: 100m, memory: 128Mi }
            limits:   { cpu: 500m, memory: 512Mi }
          readinessProbe:
            httpGet: { path: /health/ready, port: http }
            initialDelaySeconds: 10
            periodSeconds: 5
          livenessProbe:
            httpGet: { path: /health/live, port: http }
            initialDelaySeconds: 30
            periodSeconds: 15
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
```

## HPA

```yaml
spec:
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
```

## PodDisruptionBudget (Required for Tier 1)

```yaml
spec:
  minAvailable: 1
  selector:
    matchLabels: {{ include "app.selectorLabels" . | nindent 6 }}
```
