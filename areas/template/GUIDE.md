# Template authoring guide

This guide explains how to use the templates in this directory to create new specializations.

---

## The four-layer structure

Every specialization follows this layout — no exceptions:

```text
<spec-name>/
├── AGENTS.md      # Navigation index — always loaded first
├── rules/         # Constraints — always loaded for this spec
├── skills/        # Capabilities — loaded on demand
├── workflows/     # Orchestrated processes — triggered by /command
└── prompts/       # Human-copy-paste templates (EN + RU)
```

Each layer has a purpose:

| Layer | Purpose | Load behavior |
|:---|:---|:---|
| `AGENTS.md` | Maps the spec's files; sets load order | Always first |
| `rules/` | Hard constraints the agent cannot override | Always all |
| `skills/` | Technical patterns loaded for specific tasks | On demand — agent checks "When to load" |
| `workflows/` | Step-by-step processes triggered by slash commands | On /command trigger |
| `prompts/` | Copy-paste inputs for humans (bilingual) | Human reference |

---

## Step-by-step: adding a new spec

### 1. Choose the parent area

- `areas/software/` — application development domains
- `areas/devops/` — infrastructure and platform domains

If neither fits, propose a new area in a GitHub issue before creating files.

### 2. Create the directory structure

```bash
mkdir -p areas/<domain>/<spec-name>/{rules,skills,workflows,prompts}
```

### 3. Author `AGENTS.md` using `AGENTS.tmpl.md`

Fill in:
- **What this area covers** — one paragraph, specific scope
- **Inherited constraints** — what the parent area already enforces (don't repeat these in rules)
- **Spec-specific constraints** — imperatives only; no advice
- **Spec map** — every file with an inline description

### 4. Author rules using `rule.tmpl.md`

Rules are constraints, not guidelines. Each file covers one coherent concern. Ask:
- What must the agent *never* do?
- What is *required* before proceeding?
- What blocks the task (P0) vs flags for review (P1)?

### 5. Author skills using `skill.tmpl.md`

Skills are technical capabilities loaded on demand. Each skill:
- Has a precise "When to load" section
- Covers 1–3 related techniques with real code examples
- Ends with "Common mistakes" (3–5 items)

### 6. Author workflows using `workflow.tmpl.md`

Workflows are orchestrated processes. Each workflow:
- Maps to a `/command` trigger — unique across ALL areas (check the trigger registry in the area-level `AGENTS.md`)
- Has 3–8 steps with explicit roles, inputs, actions, and done-when criteria
- Names the handed-over artifact in `Input:` whenever the step role changes
- Includes at least one failure path
- Bounds every loop or retry (max iterations + escalation path) — "loop until done" is a defect
- Ends with a "Document & Version" step (delivery) or a `docs/incidents/` root-cause doc (incident), and an explicit `Next: /<trigger>` or `Next: terminal` handoff
- Has measurable quality gates in the frontmatter

### 7. Author prompts using `prompt.tmpl.md`

Prompts are bilingual (EN + RU) templates for humans to copy-paste. Each prompt:
- Links to a workflow via frontmatter
- Has 2–3 examples with realistic values (no placeholders)
- EN and RU blocks are semantically identical

### 8. Update the parent area's `AGENTS.md`

Add the new spec to the spec map and register every workflow trigger in the area's trigger registry. If this is the first spec in a new area, create the area-level `AGENTS.md` using `AGENTS-area.tmpl.md`.

### 9. Test before submitting

Run at least one workflow in a real agent session. Document the tool, model, and outcome in your PR.

---

## Quality bar

A spec is ready to submit when:

- All `AGENT INSTRUCTIONS` comment blocks are deleted.
- All `{{PLACEHOLDER}}` values are replaced with real content.
- All code examples are runnable without modification.
- File lengths are within guidelines: rules ≤ 150, skills 150–350, workflows 60–200 lines.
- Every workflow trigger is unique across all areas and registered in the area-level `AGENTS.md`.
- Every workflow loop is bounded and every cross-workflow reference is acyclic (or carries a circuit breaker).
- The spec has been tested in a real agent session.
