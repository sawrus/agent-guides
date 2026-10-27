---
description: SLI and SLO definitions, targets per tier, and the error budget actions that gate releases.
paths:
  - "**/slo*.yaml"
  - "**/slo*.yml"
  - "**/sloth/**"
  - "**/pyrra/**"
  - "**/openslo/**"
---

# SLO and error budget policy

- Define an SLI, an SLO target, and an error budget for every tier 1 service in an SLO file in the repository.
- Write each SLI as a ratio of good events to valid events (`good_requests / total_requests`), not as a raw average.
- Use availability and latency SLIs for HTTP and gRPC services, freshness or correctness SLIs for pipelines.
- Set tier 1 targets at 99.9 % (43 min budget per 28 days), tier 2 at 99.5 %, and tier 3 at 99.0 %.
- Use a 28-day rolling window for every SLO; do not use calendar months.
- Exclude only documented planned maintenance and synthetic traffic from the SLI query.
- Keep normal releases while more than 50 % of the budget remains.
- Add reliability tickets to the next iteration when 25–50 % of the budget remains.
- Stop feature releases and ship only reliability, security, and critical bug fixes when less than 25 % remains.
- Write an incident page and block feature releases until the budget recovers when the budget reaches 0 %.
- Record the approver and reason for every release made during a freeze in the release merge request.
- Review every SLO target each quarter against the measured reliability and update the SLO file.
