---
trigger: always_on
glob: env-settings-guide
description: enforce DSN-based configuration via Pydantic BaseSettings
---

# Environment & DSN Settings Rule

**Rules:**

- All service connections (DB, cache, brokers, APIs) MUST use **DSN variables**.
- Use a single DSN env var instead of splitting config into `USER/HOST/DB`.
- All configuration MUST be defined via Pydantic `BaseSettings`.
- Parsing, validation, and defaults live inside the Settings model only.

### Environment Files

- `.env.example` MUST exist and be kept up to date.
- `.env.example` MUST contain **test / placeholder credentials only**.
- `.env` MUST contain **real (production or local) credentials**.
- `.env` MUST be listed in `.gitignore`.
- `docker-compose.yml` MUST explicitly load `.env`.

**Examples:**

- ✅ `DATABASE_DSN=postgresql+asyncpg://test_user:test_pass@localhost:5432/app`
- ❌ `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_NAME`

**Violations:**

- Real credentials inside `.env.example`.
- Splitting DSN into multiple env variables.
- Accessing env vars outside `BaseSettings`.
- Missing `.env.example` or docker-compose env loading.
