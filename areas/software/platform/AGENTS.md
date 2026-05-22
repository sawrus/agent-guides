# Platform — guidance index

## What this area covers

Internal platform engineering for software teams: Kubernetes manifests, Terraform patterns, CI/CD pipeline setup, secrets management, observability stack configuration, networking, cost governance, and production incident response. The platform area bridges software development and dedicated DevOps specializations.

## Guidance chain

1. Project `.agent/` baseline (`AGENTS.md` + `.agent/*`)
2. `.agent/rules/*` — always active
3. `.agent/rules/*` — load all for this spec
4. `.agent/skills/*/SKILL.md` — load only the skill matching the current task
5. `.agent/workflows/*` — load the workflow matching the triggered command

## Spec selection

For deep platform specialization, prefer the dedicated DevOps area specs:

| Task type | Preferred spec |
|:---|:---|
| Kubernetes cluster operations | `devops/kubernetes/` |
| Terraform IaC at scale | `devops/infrastructure/` |
| Observability stack (Prometheus/Grafana) | `devops/observability/` |
| SRE / SLO / incident management | `devops/sre/` |
| CI/CD pipelines | `devops/ci-cd/` |
| General platform work in a software project | `software/platform/` ← this spec |

## Platform-specific constraints

- All infrastructure changes are version-controlled; no manual changes to shared environments.
- Cost governance: any resource creation above the defined threshold requires a cost estimate in the PR.
- Secrets are never stored in manifests, pipelines, or environment files — vault integration is mandatory.
- Incident response follows the severity classification defined in `rules/reliability.md`.

## Spec map

```text
.agent/
├── rules/
│   ├── immutability.md        ← no manual infra changes; IaC-first discipline
│   ├── reliability.md         ← SLO targets, incident severity, on-call expectations
│   ├── security-posture.md    ← image scanning, RBAC, secret hygiene
│   └── cost-governance.md     ← budget alerts, resource tagging, approval thresholds
├── skills/
│   ├── k8s-manifests/SKILL.md          ← deployment, service, ingress, HPA patterns
│   ├── terraform-patterns/SKILL.md     ← module structure, state, variable design
│   ├── ci-cd-pipelines/SKILL.md        ← GitHub Actions / GitLab CI for app teams
│   ├── secrets-management/SKILL.md     ← Vault, External Secrets Operator, rotation
│   ├── observability-setup/SKILL.md    ← Prometheus scraping, Grafana dashboards
│   ├── networking/SKILL.md             ← ingress, TLS, DNS, service mesh basics
│   └── incident-response/SKILL.md      ← triage, comms, runbook execution
├── workflows/
│   ├── provision-env.md        ← /provision-env
│   ├── deploy-production.md    ← /deploy-production
│   ├── drift-check.md          ← /drift-check
│   ├── incident-response.md    ← /incident-response
│   └── cost-audit.md           ← /cost-audit
└── prompts/
    └── *.md
```

## Discovery patterns

- `.agent/rules/*.md`
- `.agent/skills/*/SKILL.md`
- `.agent/workflows/*.md`
- `.agent/prompts/*.md`
