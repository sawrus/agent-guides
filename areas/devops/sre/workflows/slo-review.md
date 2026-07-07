---
name: slo-review
type: workflow
trigger: /slo-review
description: Conduct quarterly SLO review — evaluate current SLOs against reliability data, adjust targets, and plan error budget policy changes.
inputs:
  - quarter (e.g. Q4-2024)
  - services_to_review
outputs:
  - slo_review_report
  - updated_slo_definitions
  - error_budget_policy_changes
roles:
  - devops-engineer
  - team-lead
  - product-owner
execution:
  initiator: devops-engineer
related-rules:
  - slo-policy.md
  - error-budget-policy.md
uses-skills:
  - slo-sli-design
  - capacity-planning
quality-gates:
  - every proposed SLO target cites ≥ 30 days of measured SLI data
  - every changed SLO has product-owner sign-off
  - error budget policy reviewed for services that hit freeze state
---

## Steps

### 1. Pull Reliability Data — `@devops-engineer`
- **Input:** quarter and services_to_review from the workflow inputs.
```promql
-- 90-day availability per service
avg_over_time(
  slo:http_availability:ratio_rate5m{service="$svc"}[90d]
) * 100

-- Total error budget consumed this quarter
(
  1 - avg_over_time(
    slo:http_availability:ratio_rate5m{service="$svc"}[90d]
  )
) / (1 - 0.995) * 100   -- as % of total budget
```
- For each service: actual availability, error budget consumed, number of incidents
- **Done when:** availability, error budget consumed, and incident count collected for every service in scope.

### 2. Classify Services — `@devops-engineer`
- **Input:** per-service reliability data from step 1.

| Category | Criteria | Action |
|:---|:---|:---|
| **Overperforming** | Actual > SLO + 0.5% | Tighten SLO (stop "saving" budget by over-engineering) |
| **Meeting SLO** | Within ±0.2% | No change required |
| **Underperforming** | Budget < 25% remaining | Investigate root cause; adjust target or invest in reliability |
| **New service** | < 1 month of data | Set conservative target; review in 30 days |

- **Done when:** every reviewed service assigned a category with a proposed action.

### 3. SLO Adjustment Workshop — `@devops-engineer` + `@team-lead` + `@product-owner`
- **Input:** service classification table from step 2.

For each flagged service:
- **Tightening:** "We maintained 99.92% — can we commit to 99.9% and remove over-engineering?"
- **Loosening:** "We hit 99.3% but committed to 99.5% — is the gap a reliability problem or wrong target?"
- **New SLIs:** any new customer-visible behavior not yet covered by an SLI?
- **Done when:** each flagged service has a target decision with product-owner sign-off, and every proposed target cites ≥ 30 days of measured SLI data.

### 4. Update SLO Definitions — `@devops-engineer`
- **Input:** target decisions from the step 3 workshop.
```yaml
# Update slo/<service>.yaml (Sloth)
# Re-generate Prometheus rules
sloth generate -i slo/${SERVICE}.yaml -o rules/slo-${SERVICE}-generated.yaml
kubectl apply -f rules/slo-${SERVICE}-generated.yaml -n monitoring
```
- **Done when:** regenerated SLO rules applied to the monitoring namespace.

### 5. Error Budget Policy Review — `@team-lead` + `@product-owner`
- **Input:** workshop decision log from step 3 and updated SLO definitions from step 4.
- Did any service exhaust budget? → Was feature freeze enforced? Did it work?
- Any services that needed freeze but policy wasn't triggered? → Fix thresholds
- Review next quarter's reliability investment vs feature work ratio
- **Done when:** freeze thresholds confirmed or corrected; next quarter's reliability-vs-feature ratio agreed.

### 6. Publish SLO Review Report — `@devops-engineer`
- **Input:** decisions and updated definitions from steps 3–5.
- Commit the report to `docs/slo/<quarter>-slo-review.md`:
```markdown
# SLO Review Report — Q4 2024

| Service   | SLO Target | Actual Q4 | Budget Used | Action |
|:----------|:-----------|:----------|:------------|:-------|
| checkout  | 99.5%      | 99.71%    | 42%         | None   |
| payments  | 99.9%      | 99.82%    | 80%         | Invest |
| notify    | 99.0%      | 99.43%    | 0%          | Tighten to 99.3% |

## Decisions
- payments: allocate 20% of Q1 sprint capacity to reliability work
- notify: tighten SLO to 99.3%; generates meaningful error budget
```
- **Done when:** report committed to `docs/slo/<quarter>-slo-review.md`.

## Agent Interaction Diagram

<!-- agent-diagram:start -->
```mermaid
flowchart TD
  start(["Start /slo-review"])
  role_1["devops-engineer"]
  role_2["team-lead"]
  role_3["product-owner"]
  step_1["1. Pull Reliability Data"]
  step_2["2. Classify Services"]
  step_3["3. SLO Adjustment Workshop"]
  step_4["4. Update SLO Definitions"]
  step_5["5. Error Budget Policy Review"]
  step_6["6. Publish SLO Review Report"]
  exit(["Report published + SLO changes applied + action items in tracker = review c..."])
  start --> step_1
  step_1 --> step_2
  step_2 --> step_3
  step_3 --> step_4
  step_4 --> step_5
  step_5 --> step_6
  step_6 --> exit
  role_1 -. owns .-> step_1
  role_1 -. owns .-> step_2
  role_1 -. owns .-> step_3
  role_2 -. owns .-> step_3
  role_3 -. owns .-> step_3
  role_1 -. owns .-> step_4
  role_2 -. owns .-> step_5
  role_3 -. owns .-> step_5
  role_1 -. owns .-> step_6
```
<!-- agent-diagram:end -->

## Exit
Report published + SLO changes applied + action items in tracker = review complete.

**Next:** terminal — no follow-up workflow.
