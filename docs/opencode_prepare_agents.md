---
covers:
  - extensions/opencode/commands/**
---

# TASK: Prepare AI Agent Infrastructure

Analyze the codebase and create a complete AI-agent setup, including `AGENTS.md` and the `.agent/` directory.

## STEP 1: Project analysis

Collect the following details:

1. **Technology stack**
   - Programming language (Python/Go/Node.js/Java/Rust)
   - Framework (FastAPI/Django/Express/Spring/Gin/Actix)
   - Database (PostgreSQL/MySQL/MongoDB/Redis)
   - Build tools (poetry/npm/cargo/maven/gradle)

2. **Commands**
   - Dependency installation
   - Linting and formatting
   - Testing (full suite, single file, single test)
   - Build and run

3. **Architecture and domain**
   - Service boundaries/modules
   - Core entities and relationships
   - External integrations and infrastructure

## STEP 2: Create guidance artifacts

Create:

- `AGENTS.md` (high-level operating guidance)
- `.agent/rules/*` (non-negotiable constraints)
- `.agent/skills/*/SKILL.md` (focused execution playbooks)
- `.agent/workflows/*` (repeatable delivery flows)
- `.agent/prompts/*` (ready-to-use commands/prompts)

## STEP 3: Quality checks

- Ensure guidance matches the real stack and tooling.
- Keep instructions actionable and testable.
- Verify examples are technically accurate and production-oriented.
