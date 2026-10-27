---
name: helm-charts
description: "Procedure to change a Helm chart: edit values and templates, lint, render, validate against the cluster schema, diff against the live release, and bump the chart version. Use when you edit files under charts/ or a Chart.yaml."
---

# Helm chart: change and verify

## 1. Read the chart

1. Open `Chart.yaml`, `values.yaml`, and the templates the task touches.
2. Find the values files per environment (`values-<env>.yaml`, a helmfile, or an Argo CD / Flux manifest).
3. List chart dependencies: `helm dependency list charts/<name>`.

## 2. Make the change

1. Put every value that differs per environment in `values.yaml` with a safe default and a comment.
2. Use `required` for values without a safe default: `{{ required "image.tag is required" .Values.image.tag }}`.
3. Quote string values in templates: `{{ .Values.name | quote }}`.
4. Keep resources, probes, and security context configurable; do not hard-code them in a template.
5. If the chart has `values.schema.json`, add the new value to it.
6. Bump `version` in `Chart.yaml` for any chart change. Bump `appVersion` only when the default image changes.

## 3. Lint and render

```bash
helm dependency update charts/<name>
helm lint charts/<name> -f charts/<name>/values-<env>.yaml
helm template test charts/<name> -f charts/<name>/values-<env>.yaml > /tmp/rendered.yaml
kubeconform -strict -summary -kubernetes-version <cluster-version> /tmp/rendered.yaml
```

1. Render every environment values file, not only the default one.
2. Read the rendered output for the changed objects. Check names, labels, selectors, and image tags.
3. If the chart has unit tests (`helm unittest charts/<name>`), add a test for the change.

## 4. Diff against the live release

```bash
helm diff upgrade <release> charts/<name> -n <namespace> -f charts/<name>/values-<env>.yaml
```

1. This step reads the cluster. Ask the user first which context and namespace to use.
2. Check the diff for changes to immutable fields (`spec.selector`, `volumeClaimTemplates`). These fail the
   upgrade and need a delete and recreate; stop and tell the user.
3. Check that no Secret or PersistentVolumeClaim is deleted.

## 5. Release

1. If GitOps (Argo CD, Flux) deploys the chart, commit the change and let the controller sync it.
2. If the pipeline runs `helm upgrade`, it must use `--atomic --wait --timeout <n>m`.
3. Ask the user first before you run `helm upgrade`, `helm install`, or `helm rollback` against a cluster.
4. After the upgrade: `helm status <release> -n <namespace>` and `kubectl rollout status` for each changed
   workload.
