# Contributing to agent-guides

Thank you for improving this knowledge base. Every quality addition makes agent workflows sharper across all projects that use it.

---

## Table of contents

- [What to contribute](#what-to-contribute)
- [Project structure](#project-structure)
- [How to add content](#how-to-add-content)
- [Quality standards](#quality-standards)
- [Pull request process](#pull-request-process)
- [Review criteria](#review-criteria)

---

## What to contribute

### High-value contributions
- New skills for existing specialization areas (check the spec's `AGENTS.md` for gaps).
- New specialization areas with a full `rules/` + `skills/` + `workflows/` + `prompts/` structure.
- Improved workflow steps — more specific actions, better failure paths, clearer "Done when" criteria.
- Real-world examples in prompts (EN + RU, no placeholders, realistic values).
- Rule improvements: converting advisory language ("should", "ideally") to imperative ("must", "never").

### What to avoid
- Duplicating content already covered in `areas/software/general/`.
- Generic advice that isn't actionable by an agent (e.g., "write clean code").
- Prompt examples with placeholder values like `[YOUR_PRODUCT]` or `{{INSERT_URL}}`.
- Skill files under 150 lines (too thin — expand or fold into an existing skill).
- Workflow files over 200 lines (too long — split into two workflows).

---

## Project structure

```text
agent-guides/
├── areas/
│   ├── software/          # Application development specializations
│   │   ├── general/       # Shared baseline — all software specs inherit from here
│   │   ├── backend/
│   │   ├── frontend/
│   │   ├── full-stack/
│   │   ├── data-engineering/
│   │   ├── mlops/
│   │   ├── mobile/
│   │   ├── platform/
│   │   ├── qa/
│   │   └── security/
│   └── devops/            # Platform and operations specializations
│       ├── kubernetes/
│       ├── ci-cd/
│       ├── infrastructure/
│       ├── observability/
│       ├── sre/
│       ├── networking/
│       ├── devsecops/
│       └── database-ops/
├── extensions/
│   ├── opencode/          # opencode agent definitions and commands
│   ├── claude/            # Claude-specific configs
│   └── ...
├── areas/template/        # Authoring templates — start here for new content
├── docs/                  # Setup and usage guides
└── AGENTS.md              # Root agent guidance (loaded into every project)
```

Each specialization follows this consistent layout:

```text
<specialization>/
├── AGENTS.md       # Navigation index — load first
├── rules/          # Constraints and conventions (always loaded)
├── skills/         # Technical capabilities (loaded on demand)
├── workflows/      # Step-by-step processes (loaded on /command)
└── prompts/        # Human copy-paste templates (EN + RU)
```

---

## How to add content

### Adding a new skill

1. Identify which spec the skill belongs to (check `AGENTS.md` in that spec).
2. Create a directory: `areas/<domain>/<spec>/skills/<kebab-case-name>/`.
3. Copy `areas/template/skill.tmpl.md` → `SKILL.md` in that directory.
4. Fill all frontmatter fields; write at least 2 substantive sections + "Common mistakes".
5. Use real, runnable examples — no placeholder values.
6. Update the spec's `AGENTS.md` spec map to include the new skill.
7. Target: 150–350 lines.

### Adding a new workflow

1. Create `areas/<domain>/<spec>/workflows/<kebab-case-name>.md`.
2. Create a matching `areas/<domain>/<spec>/prompts/<kebab-case-name>.md`.
3. Use `areas/template/workflow.tmpl.md` and `areas/template/prompt.tmpl.md`.
4. Every step must have `@role`, Input, Actions (specific), and a checkable "Done when".
5. Update the spec's `AGENTS.md` spec map.
6. Target: 60–200 lines for the workflow.

### Adding a new rule

1. Create `areas/<domain>/<spec>/rules/<kebab-case-name>.md`.
2. Use `areas/template/rule.tmpl.md`.
3. Set priority P0 or P1 with a clear statement of what non-compliance causes.
4. Write constraints as imperative statements — "must", "never", "required", "forbidden".
5. Include at least one compliant and one non-compliant example.
6. Target: under 150 lines.

### Adding a new specialization area

1. Create the directory structure under `areas/<domain>/<spec>/`.
2. Start with `AGENTS.md` (use `areas/template/AGENTS.tmpl.md`).
3. Add at least one rule, one skill, and one workflow before opening a PR.
4. If adding a new domain root, also create a domain-level `AGENTS.md` (use `areas/template/AGENTS-area.tmpl.md`).

---

## Quality standards

### Rules for all contributions

- All `{{PLACEHOLDER}}` values replaced — no template strings in the final file.
- All `AGENT INSTRUCTIONS` comment blocks deleted.
- Frontmatter fields fully populated.
- Files stay within line-count targets.
- Spec map in `AGENTS.md` updated to reflect new files.

### Rules for skills

- "When to load" is specific: describes the exact task condition, not just the general topic.
- Examples are real and runnable — not abbreviated pseudocode.
- "Common mistakes" section present with at least 3 items.

### Rules for workflows

- Every step has a checkable "Done when" criterion.
- At least one step includes a documented failure path.
- Roles use the standard handle set: `@product-owner`, `@pm`, `@team-lead`, `@developer`, `@qa`, `@designer`.

### Rules for prompts

- Both EN and RU blocks present in every example.
- Blocks are semantically identical — full translation, not paraphrase.
- No placeholder values — all fields contain realistic, specific values.

---

## Pull request process

1. Fork the repository and create a branch: `feat/add-<skill-or-area-name>`.
2. Make your changes following the quality standards above.
3. Run a self-review against the authoring checklist in `areas/template/README.md`.
4. Open a PR using the provided PR template.
5. Respond to review comments within 3 business days.

### PR title format

```
feat(area/spec): add <skill|workflow|rule> for <topic>
fix(area/spec): improve <file> — <what was wrong>
docs: update <file> — <what changed>
```

---

## Review criteria

Reviewers check:

- [ ] Content is actionable by an agent — not generic advice.
- [ ] No placeholders or template strings remain.
- [ ] Line-count targets respected.
- [ ] Spec map updated in `AGENTS.md`.
- [ ] Constraints in rules use imperative language.
- [ ] Prompt examples contain no placeholder values and include both EN and RU.
- [ ] New skills have a specific "When to load" section.
- [ ] Workflow steps have checkable "Done when" criteria.

---

## Community

- Open a GitHub Discussion for questions about content direction or scope.
- Use issue templates for bug reports or new content requests.
- Be specific in issues: which file, which rule, what is wrong or missing.
