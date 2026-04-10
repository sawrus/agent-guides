# Rule: Dependency Security Policy

**Priority**: P1 — Critical exploitable dependency risk blocks release; all accepted risks require owner + expiry.

## Policy Model: Risk-Based, Not CVSS-Only

1. Triage by **exploitability context**:
   - severity (CVSS),
   - reachability from runtime code path,
   - exposure boundary (internet-facing vs internal),
   - presence of compensating controls.
2. A Critical CVE with confirmed reachable path is a deployment blocker.
3. High CVEs require remediation plan within 72h or formal exception.

## Mandatory CI Controls

4. Run dependency scanning on every PR and main build.
5. Enforce lockfiles and deterministic install modes.
6. Verify checksums/signatures when ecosystem tooling supports it.
7. Fail on prohibited licenses or policy-violating dependency sources.

## Provenance and Registry Trust

8. Prefer trusted publishers / verified maintainers where available.
9. Restrict package sources to approved registries/proxies.
10. Alert on maintainer transfer, suspicious install scripts, typosquatting indicators.

## Reachability and VEX

11. For each High/Critical finding, classify as:
   - `exploitable-now`,
   - `not-reachable`,
   - `accepted-risk` (temporary).
12. Use VEX-compatible status where possible to document non-exploitable findings.
13. “Not reachable” claims require evidence (call graph, dependency path, runtime boundary).

## Exception Handling

14. Exceptions require: owner, justification, compensating controls, expiry date (max 30 days).
15. Expired exceptions automatically re-block deployments.
16. All exceptions reviewed in weekly security triage.

## Language/Stack Constraints

17. JavaScript/TypeScript: lockfile mandatory; block lifecycle scripts unless explicitly approved.
18. Python: hashes for production requirements (`--require-hashes`) when feasible.
19. Containers: base images pinned by digest; no floating tags in production images.
