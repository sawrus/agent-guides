# AGENTS — core guidance

This file loads into every session and every subagent. Keep it short. Put details in skills, scoped rules, and
workflows.

## Load on demand

- Read a rule, skill, workflow, or prompt only when the task touches its subject. Rules live in `.agent/rules/`;
  read one when a loaded skill or workflow links it. Claude Code loads `.claude/rules/` itself.
- Run a workflow from `.agent/workflows/<name>.md` only for its command.
- Before changing project logic, read the matching design or behavior page under `docs/**`, if one exists.

## Scale the process to the task

- Trivial (a question, a one-line fix): act directly. No plan, no subagents, no extra documents.
- Small (one module, clear cause): no subagents. Make the change, run the checks, report.
- Feature or multi-module change: first state acceptance criteria and what is out of scope. Use one read-only
  explorer subagent (ours or the host's native one) only when the code is unfamiliar and too large to list with
  one command. After a diff that spans several modules, use one reviewer subagent that reports only correctness
  bugs and unmet requirements. A feature in one module needs no reviewer.
- Do not start a subagent for work that one tool call can do.
- Workflow roles (`product-owner`, `developer`, `qa`, and others) name responsibilities. Delegate a step to a role
  subagent only when that subagent is installed (`team` profile); otherwise do the step yourself.

## Definition of done

- After the last edit, run the project checks (Makefile targets such as `make test` and `make lint`, or their
  documented equivalents). Show the command and its result. Do not claim success without that output.
- Change only what the task needs. List unrelated problems in the report; do not fix them.
- A user-visible change updates `CHANGELOG.md` and the matching `docs/` page, if one exists. Bump the version and
  name the CHANGELOG section as the project's release policy says (for example `docs/release-policy.md`). Without
  a policy, write under `Unreleased`, and only a completed feature updates the project version.
- Add a new file at the repository root only after the user approves its name and purpose.
- Never run write or maintenance SQL on a non-local database. Ask before using database credentials from `.env`.

## Git

- Branch: `<type>/<task-id>-<slug>`, types `feat`, `fix`, `chore`, `docs`, `refactor`. Do not commit to `main`
  or other protected branches.
- Commits: `<type>(<scope>): <subject>`; the body says why and names the ticket.
- Never commit secrets, `.env` files, or build artifacts.

## Response language

- Write user-facing text in a plain style based on ASD-STE100: short sentences, active voice, one idea per
  sentence, consistent terms. Adapt it to the user's language. Keep code, identifiers, and quotations exact.
- Do not claim formal ASD-STE100 compliance.

## Optional layers

- Memory providers (Context7, MemPalace): read `MEMORY.md` only when those MCP tools are available.
- Post-task review: read `REVIEW_PIPELINE.md` only for a workflow with a Post-task review hook, after successful
  delivery.
