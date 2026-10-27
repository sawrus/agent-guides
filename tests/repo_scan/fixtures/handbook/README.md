# Team handbook

This repository holds team documentation only.

## Services

- order-service processes orders with rules.
- catalog-lib stores the rules and serves them over HTTP.
- shared-lib is the shared Python library for API clients.

## On-call

1. Check the alert in the monitoring channel.
2. Open the service dashboard.
3. Follow the runbook for the service.
4. Write a short note in the incident log.

## Releases

- Every service releases from the default branch.
- CI runs `make test` before a release.
- The changelog lists user-visible changes.

## Contacts

Ask in the team channel.
