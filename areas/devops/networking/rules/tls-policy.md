---
description: Protocol versions, certificate sources, renewal, and HSTS for TLS endpoints.
paths:
  - "**/certificate*.yaml"
  - "**/cluster-issuer*.yaml"
  - "**/issuer*.yaml"
  - "**/ingress*.yaml"
  - "**/nginx*.conf"
  - "**/*lb*.tf"
---

# TLS policy

- Set the minimum protocol to TLS 1.2 on every listener and disable TLS 1.0 and 1.1.
- Enable TLS 1.3 on every listener that supports it.
- Issue certificates with cert-manager `Certificate` or Ingress annotations; do not commit certificate or key files.
- Use an ACME `ClusterIssuer` (Let's Encrypt) for public hosts and a Vault PKI or internal CA issuer for internal hosts.
- Use the DNS-01 solver for wildcard certificates.
- Set `renewBefore` so certificates renew with at least 30 days left.
- Add an alert on `certmanager_certificate_expiration_timestamp_seconds` for certificates that expire in less than 14 days.
- Add the `Strict-Transport-Security` header with `max-age` of at least `31536000` on every public HTTPS host.
- Terminate TLS at the ingress or load balancer and re-encrypt to the pod when the traffic crosses an untrusted network.
