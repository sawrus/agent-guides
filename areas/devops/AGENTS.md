# DevOps — area index

Infrastructure and operations for backend services: CI/CD (GitLab first, GitHub second), Terraform and Ansible,
Kubernetes, observability, incidents, database operations, networking, and security tooling.

## Spec selection

| Task type | Spec |
|:---|:---|
| Pipelines, builds, releases | `ci-cd/` |
| PostgreSQL access, backups, migrations in production | `database-ops/` |
| Security scans, SBOM, signing, policy-as-code | `devsecops/` |
| Terraform, Ansible, environments, drift | `infrastructure/` |
| Workloads, Helm, cluster standards | `kubernetes/` |
| Ingress, network policies, TLS | `networking/` |
| Metrics, logs, alerts, SLO dashboards | `observability/` |
| Incidents, on-call, SLO policy | `sre/` |

## Load order

1. Spec `AGENTS.md` — installed into the project `AGENTS.md`.
2. Rules — Claude Code loads a rule when a file matches its `paths:`; read a `trigger: manual` rule when the
   task touches its topic.
3. Skills — on demand, when the description matches the task.
4. Workflows — when the request matches `selection.use-when` or the user types the trigger.

## Trigger registry

Triggers are unique across all areas; check `areas/software/AGENTS.md` before you add one.

| Trigger | Spec | Purpose |
|:---|:---|:---|
| `/release-pipeline` | ci-cd | Build or fix a release pipeline |
| `/security-scan` | devsecops | Scan, triage, and gate security findings |
| `/iac-change` | infrastructure | Provision, change, fix drift in, or destroy infrastructure |
| `/debug-workload` | kubernetes | Diagnose a failing workload |
| `/incident-response` | sre | Mitigate an incident and write the incident page |

## Specs in this area

```text
areas/devops/
├── ci-cd/           # pipelines, builds, releases
├── database-ops/    # access, backups, production migrations
├── devsecops/       # scans, SBOM, signing, policy-as-code
├── infrastructure/  # Terraform, Ansible, environments, drift
├── kubernetes/      # workloads, Helm, cluster standards
├── networking/      # ingress, segmentation, TLS (rules only)
├── observability/   # alerts, golden signals, retention, SLO alerts
└── sre/             # incidents, on-call, SLO policy
```
