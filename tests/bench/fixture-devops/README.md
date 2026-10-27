# orders-deploy

Kubernetes manifests for the `orders-api` service of a shop back office.

- `k8s/deployment.yaml` — the `orders-api` Deployment in the `orders` production namespace.
- `k8s/service.yaml` — the cluster Service in front of it.

Run `make test` and `make lint` before every change. Record user-visible changes in `CHANGELOG.md`.
