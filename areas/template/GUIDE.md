# Template authoring guide

This guide explains how to use the templates in this directory. Every rule, skill, and workflow must meet
[docs/artifact-standard.md](../../docs/artifact-standard.md); `make check-artifacts` checks the `auto` items.

---

## The layers of a specialization

```text
<spec-name>/
├── AGENTS.md      # Navigation index for the spec
├── rules/         # Checkable constraints, scoped by `paths:` or loaded by hand (`trigger: manual`)
├── skills/        # On-demand procedures
└── workflows/     # Ordered checklists, triggered by /command
```

| Layer | Purpose | Load behaviour |
|:---|:---|:---|
| `AGENTS.md` | Lists the spec's files in a few lines | Installed into the project `AGENTS.md` (always-on) |
| `rules/` | Constraints a reviewer can check in a diff | When a changed file matches `paths:`; `trigger: manual` rules when a skill or workflow links them. `trigger: always_on` only for rules that apply to every change in every project of the segment |
| `skills/` | Procedures the agent would not get right without them | When the task matches the skill `description` or a workflow lists it in `uses-skills` |
| `workflows/` | One ordered checklist per kind of task | On the `/command` trigger |

Every artifact costs context tokens. Add one only when it changes what the agent does in a real project and a
reviewer can check that change. Do not add roles or report files to any artifact.

---

## Step-by-step: adding content

### 1. Choose the parent area

- `areas/software/` — application development domains
- `areas/devops/` — infrastructure and platform domains

If neither fits, propose a new area in a GitHub issue before you create files.

### 2. Check that the topic is new

Search the pack for the topic first. One topic lives in one artifact (ART-C3). A rule beats a skill on the same
topic. File names must be unique across all specs of an area that can be installed together (ART-C5).

### 3. Author rules using `rule.tmpl.md`

- Scope with `paths:` globs, or use `trigger: manual`.
- Write checkable imperatives with a concrete object; at least 70 % of the list items (ART-R2).
- At most 80 lines and 1,200 tokens; code blocks at most 15 lines and 30 % of the file.

### 4. Author skills using `skill.tmpl.md`

- Write a procedure: numbered steps, decision points, exact commands, or a bundled script.
- State the trigger in `description` ("Use when ..."), or link the skill from a workflow or rule of the spec.
- `SKILL.md` at most 250 lines; references and assets at most 400 lines; code at most 40 % of `SKILL.md`.
- No framework scaffolding templates.

### 5. Author workflows using `workflow.tmpl.md`

- 3–6 steps; each step has **Do** and **Done when**.
- The first step reproduces or states the current behaviour; a change workflow ends with checks green and docs
  updated per [docs/regulation.md](../../docs/regulation.md) section 3.
- A step that touches production says "ask the user first".
- `trigger` is `/` + `name` and unique across all areas; register it in the area `AGENTS.md`.
- `selection.use-when` is a quoted sentence of at most 300 characters; `general: true` only for the single
  catch-all workflow of a top-level area.
- At most 120 lines and 1,800 tokens.
- Add at least one `Example request:` line with a realistic user request (plain words, no `/command`); there are no separate prompt files.

### 6. Update the spec and area `AGENTS.md`

List new files in the spec `AGENTS.md` and register each workflow trigger in the area trigger registry.

### 7. Check before you submit

Run `make check-artifacts` and `make lint-content`. A new artifact states in the PR which real task it changes and
why an existing artifact cannot take it.
