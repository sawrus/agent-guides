---
description: Hardening requirements for Dockerfiles and container images of backend services.
paths:
  - "**/Dockerfile"
  - "**/Dockerfile.*"
  - "**/Containerfile"
  - "**/.dockerignore"
  - "**/.trivyignore"
---

# Container security

- Pin every `FROM` image by `@sha256` digest; never use `:latest` or a tag-only reference.
- Use a multi-stage build and copy only the built artifact into the runtime stage.
- Use a minimal runtime base image (`distroless`, `-slim`, or Alpine); do not ship compilers or package managers in the runtime stage.
- Set `USER` to a numeric non-root UID (for example `USER 1000:1000`) in the final stage.
- Never `COPY` a `.env` file or pass a secret through `ARG` or `ENV`; use BuildKit `--mount=type=secret` for build secrets.
- Add `.env`, `.git`, and credential files to `.dockerignore`.
- Remove SETUID and SETGID bits in the runtime stage (`find / -perm /6000 -type f -exec chmod a-s {} +`).
- Use the exec form of `ENTRYPOINT` and `CMD` so the process receives `SIGTERM`.
- Run `trivy image --severity CRITICAL,HIGH --exit-code 1` on every built image in CI.
- Record every `.trivyignore` entry with the CVE id, the reason, a ticket reference, and a review date.
- Keep the image writable only under mounted paths so it runs with `readOnlyRootFilesystem: true`.
