# Prompt format standard (EN/RU)

This repository expects every `areas/**/prompts/*.md` file to follow a strict structure so docs generation can reliably extract examples.

## Required structure

1. YAML front matter:

```md
---
workflow: your-workflow-stem
---
```

2. Prompt header:

```md
# Prompt: `/your-workflow-stem`
```

3. Use-when line:

```md
Use when: short scenario.
```

4. Two or three examples:

```md
## Example 1 — Human-readable title

**EN:**
```
/prompt-command
...
```

**RU:**
```
/prompt-command
...
```
```

## Rules

- `workflow:` in front matter is mandatory and must match a sibling file in `workflows/<workflow>.md`.
- Prompt filename must match the workflow stem, e.g. `prompts/testing-ci-pipeline.md` for `workflows/testing-ci-pipeline.md`.
- Prompt header and every slash command inside examples must be canonical and match the workflow stem, e.g. `/testing-ci-pipeline`.
- `Workflow link command:` is deprecated and must not appear.
- Every example must include **both** EN and RU fenced code blocks.
- Every prompt must contain **2 or 3** examples.
- Keep command and input payload realistic and copy-paste ready.
- Prefer concise titles for examples.
- Generic scaffold placeholders such as `<project context>` are not allowed.

## Validation

Run local format checks:

```bash
python3 scripts/lint_prompts.py
```

Run full catalog consistency checks:

```bash
python3 scripts/build_docs_catalog.py --validate
```


## Mapping logic

Catalog builder links prompts to workflows using the prompt front matter key:

```yaml
workflow: workflow-file-name
```

Validation then requires prompt filename, header command, and example commands to match that same workflow stem.
