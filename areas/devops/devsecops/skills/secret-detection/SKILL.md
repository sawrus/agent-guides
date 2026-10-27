---
name: secret-detection
description: "Procedure to scan a repository and its history for secrets with gitleaks, triage hits, rotate a leaked secret, and add the scan to pre-commit and CI. Use when a secret leaks or when you set up secret scanning."
---

# Secret detection and leak response

## 1. Scan

```bash
gitleaks dir . --redact --report-format json --report-path /tmp/gitleaks.json   # working tree
gitleaks git . --redact --log-opts="--all"                                       # full history
```

Use `--redact` so the output does not print the secret again.

## 2. Triage each hit

1. Open the file and line. Decide: real secret, test fixture, or false positive.
2. A test fixture or false positive goes into `.gitleaks.toml` as an allowlist entry with a path or a regex and
   a comment with the reason. Do not allowlist a whole directory of source code.
3. A real secret is a leak, even if the branch was never merged. Go to step 3.

## 3. Respond to a real leak

1. Tell the user at once: which secret, where, and since which commit.
2. Rotate first. Ask the user first, because revoking the old value can break running services. Create the
   new value in the secret store, deploy it, then revoke the old one.
3. Check the provider audit log for use of the old value between the leak commit and the revocation.
4. Remove the value from the code and read it from the environment or the secret store.
5. Rewrite history only if the user asks: `git filter-repo --replace-text <file>` needs a force push and every
   clone to re-clone. Rotation is required either way; history rewrite does not undo the leak.

## 4. Prevent the next leak

1. Add the pre-commit hook:

```yaml
- repo: https://github.com/gitleaks/gitleaks
  rev: v8.21.2
  hooks:
    - id: gitleaks
```

2. Add a CI job that fails on a hit:
   - GitLab: include the `Jobs/Secret-Detection.gitlab-ci.yml` template, or run
     `gitleaks git . --redact --log-opts="$CI_MERGE_REQUEST_DIFF_BASE_SHA..HEAD"` in a job.
   - GitHub: run `gitleaks git . --redact` in a job, or enable push protection in the repository settings.
3. Add `.env` and key file patterns (`*.pem`, `*.key`) to `.gitignore`.

## 5. Done

- The full-history scan has no untriaged hits.
- Every real secret is rotated, and the old value is revoked.
- Pre-commit and CI run the scan.
