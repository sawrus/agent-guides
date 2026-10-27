---
description: Dependency sources, lockfiles, scanning, and vulnerability exceptions for application packages.
paths:
  - "package.json"
  - "package-lock.json"
  - "pnpm-lock.yaml"
  - "yarn.lock"
  - "requirements*.txt"
  - "poetry.lock"
  - "uv.lock"
  - "go.mod"
  - "go.sum"
  - "pom.xml"
  - "build.gradle*"
---

# Dependency policy

- Commit the lockfile and install with the locked mode (`npm ci`, `pip install --require-hashes`, `go mod verify`).
- Run the dependency scan on every merge request and on the main branch.
- Block the release on a Critical CVE whose vulnerable code is reachable from the service.
- Add a fix or an exception for every High CVE within 72 hours.
- Classify every High or Critical finding as `exploitable-now`, `not-reachable`, or `accepted-risk`, and attach the evidence (call path or runtime boundary) to the scan `config` for `not-reachable`.
- Add an owner, a reason, a compensating control, and an expiry date at most 30 days ahead to every exception.
- Fail the scan job when an exception has expired.
- Allow packages only from the approved registries or proxy configured in the project.
- Fail the build on a dependency with a prohibited license.
- Block npm lifecycle scripts (`--ignore-scripts`) unless the project allowlists the package.
- Check every new dependency for maintainer transfer, unexpected install scripts, and typosquatted package names before you add it.
