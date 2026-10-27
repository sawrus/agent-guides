---
description: TLS, limits, timeouts, and CORS settings for Kubernetes Ingress and Gateway resources.
paths:
  - "**/ingress*.yaml"
  - "**/ingress*.yml"
  - "**/gateway*.yaml"
  - "**/httproute*.yaml"
  - "**/charts/**/templates/ingress*.yaml"
---

# Ingress standards

- Set `spec.ingressClassName` on every Ingress; do not rely on the default class annotation.
- Add a `tls` block with a cert-manager issued secret to every production Ingress; never expose a production route over plain HTTP.
- Enable the HTTP to HTTPS redirect (`nginx.ingress.kubernetes.io/ssl-redirect: "true"` or an `HTTPRoute` redirect filter).
- Set rate limits on every public Ingress (for example `limit-rps: "100"` and `limit-connections: "20"`).
- Set `proxy-body-size` explicitly (default `"10m"`) and document any larger value in the manifest.
- Set `proxy-connect-timeout` and `proxy-read-timeout` explicitly (for example `"10"` and `"60"`).
- Set CORS origins to an explicit list; never allow `*` origins on a production host.
- Use one host per Ingress resource and name the resource after the host.
- Do not enable `nginx.ingress.kubernetes.io/configuration-snippet` or `server-snippet` annotations.
