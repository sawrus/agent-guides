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
- Role assignments (`@pm`, "one subagent per role") and required report files (`*_report.md`).
- Rules over 80 lines, skills over 250 lines, workflows over 120 lines or with more than 6 steps
  ([docs/artifact-standard.md](docs/artifact-standard.md)).
- Framework overviews and scaffolding templates the model can produce on its own.

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
├── rules/          # Checkable constraints, scoped by `paths:` or `trigger: manual`
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
4. Fill all frontmatter fields; state the trigger in `description` ("Use when ...").
5. Write a procedure: numbered steps, decision points, exact commands, or a bundled script.
6. Update the spec's `AGENTS.md` spec map to include the new skill.
7. Limit: `SKILL.md` ≤ 250 lines, code ≤ 40 % of it; references and assets ≤ 400 lines.

### Adding a new workflow

1. Create `areas/<domain>/<spec>/workflows/<kebab-case-name>.md`.
2. Create a matching `areas/<domain>/<spec>/prompts/<kebab-case-name>.md`.
3. Use `areas/template/workflow.tmpl.md` and `areas/template/prompt.tmpl.md`.
4. Write 3–6 steps. Every step has **Do** and a checkable **Done when**. Do not add roles or report files.
5. Add a `selection` block. JEV workflow routing shows it to the model as the option text:
   ```yaml
   selection:
     general: false
     use-when: "The request asks to rotate a production secret, credential or key."
     avoid-when: "The request only asks how rotation works."   # optional
   ```
   - `use-when` is required: one quoted sentence, at most 300 characters. Describe the kind of request by purpose, inputs and outputs. Do not copy a test prompt.
   - `avoid-when` is optional. Name the nearest request that belongs to another workflow.
   - `general: true` marks the catch-all workflow for ordinary requests. Each top-level area (`areas/software`, `areas/devops`) may have at most one; today it is `software/general/development-cycle-workflow`.
   - `make lint-content` fails on a missing or invalid block.
6. Update the spec's `AGENTS.md` spec map.
7. Limit: 120 lines and 1,800 tokens for the workflow.

### Adding a new rule

1. Create `areas/<domain>/<spec>/rules/<kebab-case-name>.md`.
2. Use `areas/template/rule.tmpl.md`.
3. Scope the rule with `paths:` globs, or use `trigger: manual`.
4. Write constraints as checkable imperatives with a concrete object: "Pin images by `@sha256` digest."
5. Keep code blocks short examples of the required form (≤ 15 lines each).
6. Limit: 80 lines and 1,200 tokens.

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

- The `description` trigger is specific: it describes the exact task condition, not just the general topic.
- Commands are real and runnable — not abbreviated pseudocode.

### Rules for workflows

- Every step has **Do** and a checkable **Done when** criterion.
- A step that touches production says "ask the user first".
- No roles, `agent`, or `execution.initiator`; the main session runs the workflow.

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

Versions and releases follow [docs/release-policy.md](docs/release-policy.md).

Every rule, skill, and workflow must meet [docs/artifact-standard.md](docs/artifact-standard.md). Code changes
and their docs follow [docs/regulation.md](docs/regulation.md) (Definition of Done for code and design review,
docs layout and coverage).

Two checks enforce this in CI:

- `make check-artifacts` (part of `make lint-content`) checks every `auto` requirement of the artifact standard.
  Known findings live in `scripts/check_artifacts_baseline.json`; a PR may shrink that list but must not add to
  it. Company deny terms for ART-C6 come from `AGENTIC_DENY_TERMS_FILE` outside the repository.
- `make check-docs-coverage BASE=origin/main` fails when changed code has no changed docs page whose `covers:`
  matches it. For a change without behaviour change (tests, CI, refactoring), add the commit trailer
  `Docs-Not-Needed: <reason>`.

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
- [ ] New skills state a specific trigger in `description`.
- [ ] Workflow steps have **Do** and checkable **Done when** criteria.
- [ ] `make check-artifacts` reports no new findings and `make check-docs-coverage` passes.

---

## Community

- Open a GitHub Discussion for questions about content direction or scope.
- Use issue templates for bug reports or new content requests.
- Be specific in issues: which file, which rule, what is wrong or missing.
