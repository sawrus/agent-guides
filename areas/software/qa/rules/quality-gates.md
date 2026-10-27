---
description: Thresholds that block a merge or a deploy, enforced as CI jobs.
paths:
  - ".gitlab-ci.yml"
  - ".github/workflows/**"
  - "**/jest.config.*"
  - "**/pytest.ini"
  - "pyproject.toml"
---

# Quality gates

- Fail the merge pipeline when any unit or integration test fails.
- Fail the merge pipeline when line coverage of business logic drops below 80% or below the target branch value.
- Fail the merge pipeline on any type check or lint error.
- Fail the merge pipeline on a Critical or High SAST finding and on a Critical dependency CVE.
- Block a deploy when the smoke test suite has any failure.
- Block a deploy when p99 latency in the performance test grows by more than 20% against the baseline.
- Block a deploy when the end-to-end regression suite pass rate is below 98%.
