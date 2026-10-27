---
description: Service configuration through environment variables, settings classes, and env example files.
paths:
  - "**/settings*.py"
  - "**/config*.py"
  - "**/config/**"
  - "**/application*.yml"
  - "**/application*.yaml"
  - "**/application*.properties"
  - ".env.example"
---

# Configuration

- Read configuration only through one settings object (Pydantic `BaseSettings`, Spring `@ConfigurationProperties`, a Go config struct); no `os.getenv` calls elsewhere.
- Validate configuration at startup and fail with a clear error when a required variable is missing.
- Use one DSN variable per connection (`DATABASE_URL`, `REDIS_URL`); do not split it into host, user, and password variables.
- Keep `.env.example` in the repository with every variable and placeholder values only.
- Add `.env` to `.gitignore`; never commit a file with real credentials.
- Do not put secrets in default values of settings fields.
- Name variables in upper snake case with a service prefix when several services share an environment.
- Document each new variable in `.env.example` and the service docs page in the same change.
- Keep environment-specific values out of code; no `if env == "prod"` branches for config values.
