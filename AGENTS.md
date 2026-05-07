# AGENTS — root guidance

## Dynamic loading of guidance

The set of loaded guidance is configurable per project and may change per task. Do not assume only statically listed
files are available.

Discover and load custom files from the target project when present:

```text
project_dir/
└── .agent/
    ├── rules/
    ├── skills/
    ├── workflows/
    └── prompts/
```

**Discovery patterns:**

- `project_dir/.agent/rules/*`
- `project_dir/.agent/skills/*`
- `project_dir/.agent/workflows/*`
- `project_dir/.agent/prompts/*`

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
- Use documentation paths that match the change type, for example `docs/<feature>/README.md` for feature behavior and `docs/incidents/<date>-<workload>-root-cause.md` for incident root cause reports.
- Create or update the relevant `docs/` artifact in the same change set; do not leave behavior changes documented only in workflow outputs, tickets, or PR comments.
- Apply the `product-owner` role to confirm that docs describe the user-facing behavior, acceptance criteria, and operational constraints of the change.

### Context7 Knowledge Source

- Use Context7 for framework, library, SDK, API, and setup documentation before relying on model memory.
- Resolve the library or framework identity first, then request focused docs for the exact task and version when version matters.
- If Context7 is unavailable, state that explicitly and fall back to local docs or official project documentation.

### MemPalace + Context Strategy

- If MemPalace MCP is enabled and available, load project business/domain context from MemPalace first.
- If Context7 MCP is enabled and available, use it specifically for framework/library/API documentation.
- If both are available, combine them: MemPalace for project/business knowledge, Context7 for framework-level references.
- If MCP providers are unavailable, continue with standard local-repo discovery and context-building as fallback.

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
