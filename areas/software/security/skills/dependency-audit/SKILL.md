---
name: dependency-audit
description: "Procedure to audit dependencies of a Python, Go, Java, or Node project: scan, check reachability, classify each finding, and fix or record an exception. Use when you add or update dependencies, triage a vulnerability alert, or prepare a release."
---

# Dependency audit

## 1. Inventory the change

1. Diff the lock files against the target branch: `git diff origin/main -- '*.lock' go.sum pom.xml
   requirements*.txt package-lock.json`.
2. For each new or upgraded package, record: name, old and new version, direct or transitive, registry.
3. Check new direct packages for red flags: a maintainer change just before the release, install scripts with
   network calls, obfuscated code, a name close to a popular package, a registry outside the approved list.
   If you find one, stop and tell the user.

## 2. Scan

| Stack | Command |
|---|---|
| Python | `pip-audit -r requirements.txt` or `uv run pip-audit` |
| Go | `govulncheck ./...` |
| Java (Maven) | `mvn org.owasp:dependency-check-maven:check` or `osv-scanner -L pom.xml` |
| Node | `npm audit --omit=dev` |
| Any lock file | `osv-scanner scan source -r .` |

Record each High or Critical finding with the advisory id, the package path, and the fixed version.

## 3. Check reachability

1. Go: `govulncheck` reports only vulnerable functions that the code calls; trust its "not called" result.
2. Other stacks: search the code for the vulnerable function or feature named in the advisory.
3. Check exposure: is the code path reachable from a public endpoint, from user input, or only from tests and
   build tools?

## 4. Classify and act

- **Exploitable** — reachable from untrusted input. Upgrade to the fixed version now. Block the release until it
  ships.
- **Not reachable** — record the evidence (search result, `govulncheck` output) in the ignore file of the scanner
  with a reason, for example `.osv-scanner.toml` `[[IgnoredVulns]]` with `reason` and `ignoreUntil`.
- **No fix available** — agree with the user on a compensating control (input validation, feature off, WAF rule)
  and record an exception with an owner and an expiry date.

## 5. Fix

1. Prefer the smallest upgrade that contains the fix. Run the full test suite after it.
2. If the upgrade is a major version, read its changelog for breaking changes and fix the call sites.
3. For a transitive package, upgrade the direct parent first; pin the transitive version only if no parent
   release has the fix (`constraints.txt`, Maven `dependencyManagement`, `overrides` in `package.json`,
   `replace` in `go.mod`).

## 6. Done

- The scan shows no unexcepted High or Critical finding.
- Every exception has a reason, an owner, and an expiry date.
