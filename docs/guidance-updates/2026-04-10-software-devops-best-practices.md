# Guidance Update — Software & DevOps Best Practices (2026-04-10)

## Summary

This update strengthens repository guidance in five high-impact areas:

1. Supply-chain security moved to keyless-first signing, attestations, and admission enforcement.
2. Release workflow upgraded with database compatibility gates, progressive delivery, and explicit rollback criteria.
3. Dependency security moved from CVSS-only to exploitability-aware triage with exception governance.
4. Backend/full-stack security rules expanded for modern cloud-native threats and service identity controls.
5. Observability and alerting standards aligned to SLO-first operations with burn-rate policy and telemetry cost controls.

## Why this update

- Reduce production risk from software supply-chain and dependency compromise.
- Improve release safety for schema and high-risk feature changes.
- Align operational controls with modern SRE and platform governance practices.
- Increase actionability and signal quality in observability/alerting.

## Impacted areas

- `areas/devops/ci-cd/*`
- `areas/software/security/*`
- `areas/software/full-stack/rules/security-guide.md`
- `areas/software/backend/rules/security.md`
- `areas/devops/observability/rules/*`
