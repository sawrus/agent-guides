---
covers:
  - scripts/lint_prompts.py
  - scripts/build_docs_catalog.py
  - scripts/sync_workflow_diagrams.py
---

# Workflow example requests

The pack has no prompt files. `agentic` does not install `areas/**/prompts/*.md`, and an upgrade removes prompt
files that an older release installed when they are unchanged. A workflow carries its own example instead.

## Format

Put one or more lines in the workflow body, outside the frontmatter, each at the start of a line:

```md
Example request: The login form accepts an empty password; fix it and add a regression test.
```

`**Example request:** <text>` also works. Quotes or backticks around the text are removed.

Rules:

- Write the request as a user would type it, without the `/<workflow>` command.
- Use a concrete object (endpoint, file, service, pipeline). No placeholders such as `<project context>`.
- English. One line per request.

## Where the lines go

- `scripts/build_docs_catalog.py` puts them into `examples` (a list of strings) of each workflow in
  `docs/site/catalog.json`. `use_when` comes from `selection.use-when`. The site shows them under
  "Example requests".
- `scripts/assess_area_quality.py` warns about a workflow without such a line.

## Validation

```bash
python3 scripts/lint_prompts.py --strict      # skills and workflow selection blocks
python3 scripts/build_docs_catalog.py --validate --require-examples
```

`make lint-content` runs the catalog check without `--require-examples`.
