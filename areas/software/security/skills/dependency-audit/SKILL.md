# Skill: Dependency Audit

## When to load

When adding/updating dependencies, handling security findings, preparing releases, or reviewing supply-chain risk in PRs.

## Objective

Produce a dependency risk decision based on exploitability and business impact, not scanner output alone.

## Audit Workflow

1. **Inventory**
   - Identify direct and transitive dependencies changed in PR/release.
   - Record package source (registry), maintainer trust indicators, and version deltas.

2. **Scan**
   - Run ecosystem-native audit tools + repository policy checks.
   - Capture High/Critical findings with package path and affected components.

3. **Exploitability Triage**
   - Determine runtime reachability (is vulnerable code path invoked?).
   - Evaluate exposure (public endpoint, privileged process, internal-only).
   - Assess mitigations (WAF, sandbox, feature flags, auth boundaries).

4. **Classify each finding**
   - `exploitable-now` → block release, fix immediately.
   - `not-reachable` → document evidence and add VEX status.
   - `accepted-risk` → temporary exception with owner + expiry.

5. **Remediation Plan**
   - Prefer upgrade to patched version.
   - If upgrade is breaking: isolate vulnerability, add compensating controls, schedule upgrade milestone.

## Supply-Chain Red Flags

- Maintainer transfer shortly before suspicious release.
- Sudden dependency graph expansion unrelated to package purpose.
- install/postinstall scripts performing unexpected network activity.
- Obfuscated source in runtime package.
- Package source not in approved registries.

## Output Template (required)

- Dependency name and version delta
- Severity and advisory source
- Reachability evidence
- Classification (`exploitable-now` / `not-reachable` / `accepted-risk`)
- Decision and next action
- Owner and deadline
