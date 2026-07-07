# DevOps — area guidance index

Load this file before any spec-level guidance in `areas/devops/`.

## What this area covers

Infrastructure and platform operations: CI/CD pipelines, Kubernetes clusters, infrastructure-as-code, networking,
observability, database operations, security tooling, and site reliability. Used by agents executing operational
changes where mistakes affect production availability — every spec assumes changes are staged, verified, and
documented before being declared done.

## Spec selection

Match the task to the spec that owns it:

| Task type | Spec to load |
|:---|:---|
| Pipelines, builds, releases | `ci-cd/` |
| Postgres / Redis operations, backups, DB incidents | `database-ops/` |
| Security scanning, policy-as-code, supply chain | `devsecops/` |
| Terraform / IaC, environments, drift | `infrastructure/` |
| Clusters, workloads, Helm, RBAC | `kubernetes/` |
| Ingress, service mesh, TLS, DNS | `networking/` |
| Metrics, logs, traces, alerting, SLO dashboards | `observability/` |
| Incidents, postmortems, SLO reviews, on-call | `sre/` |

If the task spans multiple specs, load the primary spec's full chain, then the secondary spec's `rules/*` only.

## Cross-cutting constraints

- **Standard roles** — workflows use only: `product-owner`, `pm`, `team-lead`, `developer`, `qa`, `designer`,
  `devops-engineer`. No parenthetical annotations; the initiator appears in the workflow's own `roles` list.
- **Bounded loops** — every retry or iteration states a maximum (default 3) and an escalation path; cross-workflow
  trigger chains are acyclic or carry a circuit breaker.
- **Verify after change** — the last mutating step is followed by a verification step; never end on an unverified change.
- **Document outcomes** — incident workflows end with `docs/incidents/<date>-<slug>-root-cause.md`; delivery
  workflows end with a Document & Version step (docs + CHANGELOG + version source).
- **No destructive action without a verified backup** — and if backup verification itself fails, escalate to a human;
  do not enter an incident loop that requires the failed backup.

## Load order

1. This file (`areas/devops/AGENTS.md`)
2. Spec `AGENTS.md` (`areas/devops/<spec>/AGENTS.md`)
3. Spec `rules/*.md` — all rules for the selected spec
4. Spec `skills/*/SKILL.md` — on-demand, matching "When to load"
5. Spec `workflows/*.md` — matching the slash command trigger

## Trigger registry

Every workflow trigger in this area. Triggers are unique across ALL areas — check `areas/software/AGENTS.md` too
before adding one.

| Trigger | Spec | Purpose |
|:---|:---|:---|
| `/onboard-repo` | ci-cd | Add a repository to CI |
| `/pipeline-debug` | ci-cd | Diagnose failing pipelines |
| `/release-pipeline` | ci-cd | Ship a production release |
| `/backup-verify` | database-ops | Verify backup restorability |
| `/db-incident` | database-ops | Handle a database incident |
| `/policy-onboard` | devsecops | Roll out a policy-as-code control |
| `/security-scan-pipeline` | devsecops | Add security scanning to CI |
| `/provision-environment` | infrastructure | Create an environment via IaC |
| `/destroy-environment` | infrastructure | Decommission an environment |
| `/drift-remediation` | infrastructure | Reconcile infrastructure drift |
| `/module-development` | infrastructure | Build a reusable IaC module |
| `/cluster-bootstrap` | kubernetes | Stand up a new cluster |
| `/onboard-service` | kubernetes | Deploy a service to Kubernetes |
| `/debug-workload` | kubernetes | Diagnose a failing workload |
| `/upgrade-cluster` | kubernetes | Upgrade a cluster version |
| `/onboard-ingress` | networking | Expose a service via ingress |
| `/service-mesh-onboard` | networking | Add a service to the mesh |
| `/alert-investigation` | observability | Investigate a firing alert |
| `/observability-stack-setup` | observability | Deploy the observability stack |
| `/onboard-service-monitoring` | observability | Instrument and monitor a service |
| `/incident-response` | sre | Coordinate an active incident |
| `/postmortem` | sre | Produce a postmortem |
| `/slo-review` | sre | Review and adjust SLOs |

## Specs in this area

```text
areas/devops/
├── ci-cd/           # pipelines, builds, releases
├── database-ops/    # Postgres/Redis operations, backups
├── devsecops/       # scanning, policy-as-code, supply chain
├── infrastructure/  # Terraform, environments, drift
├── kubernetes/      # clusters, workloads, Helm, RBAC
├── networking/      # ingress, mesh, TLS, DNS
├── observability/   # metrics, logs, traces, alerting
└── sre/             # incidents, postmortems, SLOs
```
