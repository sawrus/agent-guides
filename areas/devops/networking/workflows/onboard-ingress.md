---
name: onboard-ingress
type: workflow
trigger: /onboard-ingress
description: Expose a Kubernetes service externally — Ingress, TLS, rate limiting, MetalLB (bare-metal).
inputs:
  - service_name
  - hostname
  - tls_source (letsencrypt|internal-ca|manual)
outputs:
  - ingress_resource
  - tls_certificate_issued
  - service_accessible
roles:
  - devops-engineer
execution:
  initiator: developer
related-rules:
  - ingress-standards.md
  - tls-policy.md
uses-skills:
  - ingress-patterns
  - tls-termination
quality-gates:
  - TLS certificate issued (not just pending)
  - HTTPS accessible; HTTP redirects
  - Rate limiting verified with load test
---

## Steps

### 1. Write Ingress Manifest — `@devops-engineer`
- Include all mandatory annotations (ssl-redirect, rate-limit, security headers, timeouts)
- Set cert-manager annotation matching chosen issuer
- **Done when:** `kubectl apply --dry-run=server` passes

### 2. Apply & Wait for Certificate — `@devops-engineer`
```bash
kubectl apply -f ingress.yaml
# Watch certificate issuance (Let's Encrypt: up to 2 min; internal CA: < 30s)
kubectl get certificate -n <ns> -w
kubectl describe certificate <cert-name> -n <ns>   # check events if stuck
```

### 3. Verify HTTPS — `@devops-engineer`
```bash
curl -v https://<hostname>/health
# Check: TLS version, cipher, cert expiry, HSTS header
```

### 4. Verify Rate Limiting — `@devops-engineer`
```bash
# Quick rate limit test (expect 429 after N requests)
for i in $(seq 1 200); do
  curl -s -o /dev/null -w "%{http_code}\n" https://<hostname>/health
done | sort | uniq -c
```

### 5. DNS (if needed) — `@devops-engineer`
- Point hostname to MetalLB external IP: `kubectl get svc -n ingress-nginx`
- Add A record in DNS provider or internal CoreDNS

## Exit
HTTPS accessible + cert issued + security headers present + rate limit verified = ingress onboarded.
