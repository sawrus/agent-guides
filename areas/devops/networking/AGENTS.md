# Networking — guidance index

## What this area covers

Platform networking: Kubernetes ingress design, TLS termination, service mesh onboarding, DNS management, VPC design, and network segmentation. Networking changes are high-blast-radius — this area enforces a plan-review-apply discipline.

## Cross-cutting constraints

- **TLS everywhere** — plaintext traffic is forbidden between services and at ingress, without exception.
- **Network segmentation by default** — all services start with deny-all; allow only documented traffic.
- **DNS changes have TTL awareness** — all DNS modifications account for TTL propagation before declaring success.
- **No routing changes without rollback** — every networking change includes a verified rollback procedure.

## Spec map

```text
.agent/
├── rules/
│   ├── tls-policy.md               ← minimum TLS version, cert rotation, mTLS requirements
│   ├── ingress-standards.md        ← ingress class, annotations, rate limiting, WAF baseline
│   └── network-segmentation.md     ← namespace isolation, egress controls, VPC peering rules
├── skills/
│   ├── ingress-patterns/SKILL.md    ← NGINX / Traefik / Gateway API patterns
│   ├── tls-termination/SKILL.md     ← cert-manager, Let's Encrypt, mTLS between services
│   ├── service-mesh/SKILL.md        ← Istio / Linkerd traffic management, observability
│   ├── dns-management/SKILL.md      ← external-dns, split-horizon, TTL strategy
│   └── vpc-design/SKILL.md          ← subnet strategy, NAT, VPC peering, PrivateLink
├── workflows/
│   ├── onboard-ingress.md         ← /onboard-ingress
│   └── service-mesh-onboard.md    ← /service-mesh-onboard
└── prompts/
    └── *.md
```
