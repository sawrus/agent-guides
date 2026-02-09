---
trigger: always_on
glob: project-guide
description: agent execution rules and project workflow
---

# Project Directive

**Core Principle:** Artifact First

- Non-trivial tasks start with artifacts; no immediate coding.

**Artifact Protocol:**

- Plan first: `artifacts/plan_<task_id>.md`
- Evidence: test logs in `artifacts/logs/`
- UI changes: `Generates Artifact: Screenshot`

**Mission & Context:**

- Read `mission.md` before work.
- Review full `src/` tree before architecture.

**Agent Behavior:**

- Confirm full plan before execution.
- Optimize code for AI readability & context efficiency.
- Prefer explicit structure to implicit behavior.

**Execution Safety:**

- Run tests after logic changes.
- Browser only for read-only verification.
- Never execute destructive system commands.
