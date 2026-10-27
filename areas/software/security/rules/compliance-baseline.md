---
description: Minimum compliance controls for services that store user data, with PCI DSS and GDPR additions.
trigger: manual
---

# Compliance baseline

- Enable encryption at rest for every database `table` store, bucket, and volume that holds user data.
- Allow only TLS 1.2 or later on every endpoint.
- Log every admin action with the actor identity and keep the audit log for at least 1 year.
- Back up user data daily and test a restore at least every quarter.
- Patch Critical vulnerabilities from the weekly scan within 7 days.
- Never store card data after authorization; keep only the payment provider token.
- Put the cardholder data environment in its own network `namespace` or segment when the service handles card data.
- Keep a data processing inventory for EU or California user data, and complete deletion requests within 30 days.
- Document the breach notification steps with the 72-hour GDPR deadline.
