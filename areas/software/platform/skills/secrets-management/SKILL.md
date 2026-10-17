---
name: secrets-management
description: "Defines a secrets hierarchy, the ExternalSecrets pattern, and a rotation checklist; use when provisioning a new service, rotating credentials, or setting up CI/CD secrets."
---

# Skill: Secrets Management

## When to load

When provisioning a new service, rotating credentials, or setting up CI/CD secrets.

## Secrets Hierarchy

```
Level 1: Static secrets (rotate quarterly)
  → AWS Secrets Manager / HashiCorp Vault
  → Database passwords, API keys for external services

Level 2: Dynamic secrets (auto-expire, 1 hour)
  → Vault dynamic secrets / AWS IAM OIDC roles

Level 3: Runtime injection (never on disk)
  → K8s ExternalSecrets Operator → mounts as env vars
  → Never in container image or Git
```

## ExternalSecrets Pattern

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
spec:
  refreshInterval: 1h
  secretStoreRef: { kind: ClusterSecretStore, name: aws-secretsmanager }
  data:
    - secretKey: DATABASE_URL
      remoteRef: { key: prod/api/database, property: connection_string }
    - secretKey: STRIPE_SECRET_KEY
      remoteRef: { key: prod/api/stripe, property: secret_key }
```

## Rotation Checklist

- [ ] New secret created, old secret still active
- [ ] Service updated to accept both (dual-read window)
- [ ] New secret deployed and verified
- [ ] Old secret revoked
- [ ] Rotation documented (next rotation: +90 days)
