---
name: slo-implementation
description: "Procedure to define an SLO for a service and implement it in Prometheus: choose the SLI, write recording rules, and add multi-window multi-burn-rate alerts. Use when you add or change an SLO, an error budget, or burn-rate alerts."
---

# SLO: define and implement

## 1. Choose the SLI

1. Pick one user journey per SLO (for example "checkout API responds").
2. Choose the SLI type:
   - **Availability** — good events / valid events, for example non-5xx responses / all responses.
   - **Latency** — requests faster than a threshold / all requests, from a histogram bucket.
3. Measure as close to the user as the data allows: load balancer or ingress metrics before application
   metrics.
4. Exclude invalid events (health checks, 4xx caused by the client) in the label selector, and write down why.

## 2. Set the target

1. Read the last 4 weeks of the SLI. Set the target slightly below what the service achieves, not above it.
2. Use a 28-day or 30-day rolling window.
3. Compute the error budget: `1 - target`. A 99.9% target gives 43 minutes of full outage per 30 days.
4. Record the SLO in the service docs page: SLI query, target, window, owner.

## 3. Write recording rules

Record the error ratio for each alert window: 5m, 30m, 1h, 2h, 6h, 1d, 3d.

```yaml
- record: slo:sli_error:ratio_rate5m
  labels: {slo: checkout-availability}
  expr: |
    sum(rate(http_requests_total{service="checkout",code=~"5.."}[5m]))
    / sum(rate(http_requests_total{service="checkout"}[5m]))
```

Repeat the rule per window (change only `[5m]` and the name). If the project uses Sloth or Pyrra, write the SLO
spec file instead and let the tool generate these rules.

## 4. Add burn-rate alerts

Use two windows per alert, so it fires fast and resets fast. For a 99.9% target (budget `0.001`):

| Severity | Long window | Short window | Burn rate | Budget spent |
|---|---|---|---|---|
| page | 1h | 5m | 14.4 | 2% |
| page | 6h | 30m | 6 | 5% |
| ticket | 3d | 6h | 1 | 10% |

```yaml
- alert: CheckoutAvailabilityBurnFast
  expr: |
    slo:sli_error:ratio_rate1h{slo="checkout-availability"} > (14.4 * 0.001)
    and slo:sli_error:ratio_rate5m{slo="checkout-availability"} > (14.4 * 0.001)
  labels: {severity: page}
```

## 5. Test and check

1. `promtool check rules <file>` and a `promtool test rules` case that fires the fast-burn alert.
2. Query the recording rules after deploy; each must return one series per SLO.
3. Add an SLO panel (SLI, target, remaining budget) to the service dashboard.

## 6. Use the budget

- Budget left: changes ship as usual.
- Budget spent in the window: write it into the service docs page and agree with the user which reliability
  work comes before new features. Do not lower the target to recover the budget.
