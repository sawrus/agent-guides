---
description: Docker Compose files for local multi-service development.
paths:
  - "**/docker-compose*.yml"
  - "**/docker-compose*.yaml"
  - "**/compose*.yml"
  - "**/compose*.yaml"
---

# Docker Compose

- Keep the base config in `compose.yaml` (or `docker-compose.yml`) and local overrides in `compose.override.yaml`.
- Pin every image to a version tag or digest; never use `latest` in a committed file.
- Load configuration from `.env` with `env_file`; never write credentials into the compose file.
- Add `.env` to `.gitignore` and keep `.env.example` next to the compose file.
- Define a `healthcheck` for every database, cache, and broker service.
- Use `depends_on` with `condition: service_healthy` for services that need a healthy dependency.
- Use named volumes for data; use bind mounts only for source code in development.
- Expose only the ports a developer needs on the host; services talk to each other by service name.
- Do not bind-mount the home directory, `/`, or `/var/run/docker.sock` unless the service needs it and a comment says why.
