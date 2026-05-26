# AGENTS — root guidance

## Dynamic guidance loading

The loaded guidance set is project-specific and may change per task. Do not assume the statically listed files are
complete; first discover optional guidance under the target project's `.agent/` directory.

Discover and load guidance in this order:

1. `.agent/*.md` — project baseline files, when present
2. `.agent/rules/*.md` — all project rules
3. `.agent/skills/*/SKILL.md` — only the skill matching the current task
4. `.agent/workflows/*.md` — only the workflow matching the triggered command
5. `.agent/prompts/*.md` — only when explicitly requested or referenced by loaded guidance

Prefer relative paths in references inside markdown files.

---

## General Development Practices

Cross-cutting practices that apply to every project regardless of area.

### Git Workflow

- Use feature branches with task IDs in branch names (e.g., `feat/TASK-123-add-auth`).
- Commit messages include context: what changed, why, and any relevant ticket reference.
- No direct commits to main or protected branches — all changes via reviewed PRs.

### Makefile Conventions

- Use Makefile for common development tasks accessible to all contributors.
- Include a `help` target listing available commands with descriptions.
- Standard targets: `install`, `dev`, `test`, `lint`, `fmt`, `clean`, `build`.

### Docker Compose

- Use docker-compose for local multi-service development.
- Configure health checks for all dependent services before marking ready.
- Drive configuration via environment variables; no hardcoded values.

### Linting and Formatting

- Configure language-appropriate linters for every project.
- Enforce standards via pre-commit hooks — CI is a safety net, not the primary check.
- Apply consistent formatting across all files on every commit.

### SDLC Methodology

- Follow phases in order: Requirements → Design → Implementation → Verification → Deployment → Maintenance.
- Document requirements before implementation — "we'll figure it out" is not a requirement.
- Conduct design reviews for any change with architectural, security, or data model impact.
- Before changing project logic, read the relevant design and behavior documents under `docs/**`.
- Run validation, tests, coverage, and CI-style checks through Makefile targets only.

### Documentation of Behavior Changes

- Any behavior change captured in Markdown artifacts must be documented under the project `docs/` directory.
- Use documentation paths that match the change type, for example `docs/<feature>/README.md` for feature behavior and
  `docs/incidents/<date>-<workload>-root-cause.md` for incident root cause reports.
- Create or update the relevant `docs/` artifact in the same change set; do not leave behavior changes documented only
  in workflow outputs, tickets, or PR comments.
- Apply the `product-owner` role to confirm that docs describe the user-facing behavior, acceptance criteria, and
  operational constraints of the change.

### MCP Memory Providers

See [MEMORY.md](MEMORY.md) for the full protocol: provider roles, Context7 usage, MemPalace session-start queries,
fact-writing triggers, tool call examples, and fallback order.

### Code Style

- Write self-documenting code with meaningful names — comments explain why, not what.
- Apply DRY principles; avoid duplication across modules.
- Keep functions focused on a single responsibility; extract when a function does two things.

---

## Repository Exploration (mandatory before implementation)

Before executing any workflow, spawn a subagent to explore the repository.

### Role resolution

- Use the role defined in `execution.initiator` of the current workflow.
- If not defined, use the role assigned to the first workflow step.
- Resolve roles only from the current workflow's `roles` section — do not invent roles.

### Purpose

- Understand current architecture and established conventions.
- Identify key modules, entrypoints, and data flows.
- Detect configuration (env, Docker, Makefile, CI).
- Identify components impacted by the proposed change.
- Validate feasibility before any code is written.

### Subagent responsibilities

- Analyze repository structure and dependencies.
- Locate relevant services, modules, and data flows.
- Identify constraints, risks, and integration points.
- Prepare a context summary for the next workflow step.

### Required output

- High-level system overview.
- List of affected modules and files.
- Detected risks and constraints.

### Constraint

This step is **mandatory** and must complete before "Solution Design & Risk Plan" begins.
