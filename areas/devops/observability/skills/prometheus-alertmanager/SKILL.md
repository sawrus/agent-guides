---
name: prometheus-alertmanager
description: "Procedure to add or change a Prometheus alerting or recording rule and its Alertmanager route, with promtool unit tests and amtool route checks. Use when you edit Prometheus rule files, PrometheusRule objects, or alertmanager.yml."
---

# Prometheus alert: add or change

## 1. Find where rules live

1. Rule files (`*.rules.yml`, `rules/*.yml`) loaded by `rule_files:` in `prometheus.yml`, or `PrometheusRule`
   objects for the Prometheus Operator, or a Helm chart values block.
2. The Alertmanager config: `alertmanager.yml` or an `AlertmanagerConfig` object.
3. Existing alerts for the same service: reuse their labels (`severity`, `team`, `service`).

## 2. Write the query first

1. Run the expression in the Prometheus UI or with `promtool query instant <url> '<expr>'` against real data.
2. Alert on symptoms users see (error ratio, latency, saturation), not on every cause.
3. Use a ratio for errors: `sum(rate(http_requests_total{code=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))`.
4. If the query is expensive or reused, add a recording rule named `level:metric:operations`, for example
   `service:http_requests:rate5m`.

## 3. Write the rule

```yaml
- alert: CheckoutHighErrorRate
  expr: service:http_errors:ratio_rate5m{service="checkout"} > 0.05
  for: 10m
  labels:
    severity: page
  annotations:
    summary: "checkout 5xx ratio above 5% for 10m"
    runbook_url: "https://wiki.example.com/runbooks/checkout-errors"
```

- Set `for:` so one scrape spike does not page.
- Use only the severities that the Alertmanager routes know (for example `page`, `ticket`).
- Every paging alert has a `runbook_url`.

## 4. Test the rule

```bash
promtool check rules rules/checkout.rules.yml
promtool test rules tests/checkout.test.yml
```

Write a unit test with `input_series` that fires the alert and one that does not:

```yaml
rule_files: [../rules/checkout.rules.yml]
tests:
  - interval: 1m
    input_series:
      - series: 'service:http_errors:ratio_rate5m{service="checkout"}'
        values: '0.1x20'
    alert_rule_test:
      - eval_time: 15m
        alertname: CheckoutHighErrorRate
        exp_alerts: [{exp_labels: {severity: page, service: checkout}}]
```

## 5. Check the route

```bash
amtool check-config alertmanager.yml
amtool config routes test --config.file=alertmanager.yml severity=page service=checkout
```

The output must name the receiver you expect. If it names the default receiver, add a route.

## 6. Ship

1. Commit the rule, the test, and the route change together.
2. After the change reaches Prometheus, check `/rules` or `/api/v1/rules` for the rule state and errors.
3. Ask the user first before you reload a production Prometheus or Alertmanager by hand
   (`curl -X POST <url>/-/reload`).
