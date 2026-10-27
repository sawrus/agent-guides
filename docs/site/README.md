---
covers:
  - scripts/build_docs_catalog.py
---

# Markdown docs site (search + menu)

This prototype renders a documentation site directly from markdown-derived catalog data.

## Why this stack

The user requirement was: site from markdown with search and menu. We evaluated popular GitHub projects:

- docsify: https://github.com/docsifyjs/docsify
- MkDocs: https://github.com/mkdocs/mkdocs
- Docusaurus: https://github.com/facebook/docusaurus
- markdown-it (parser): https://github.com/markdown-it/markdown-it

For this repo we keep it lightweight and dependency-minimal:

- catalog is generated offline by `scripts/build_docs_catalog.py` (standard library only) from
  `areas/*/*/rules/*.md`, `areas/*/*/skills/*/SKILL.md`, and `areas/*/*/workflows/*.md`
- site is static HTML/CSS/JS (`index.html`, `app.js`, `styles.css`)
- markdown rendering via `marked` CDN, full-text search via `lunr` CDN (both pinned to a version)

## Run locally

```bash
make build-docs
python3 -m http.server 8000
# open http://localhost:8000/docs/site/
```

## Features

- Left menu: area (`software`, `devops`) → spec (`backend`, `ci-cd`, ...) → three groups: Rules, Workflows, Skills.
- The start page lists every spec with the first paragraph of its `AGENTS.md` and its counts.
- Search (lunr) over rules, workflows, and skills: name, trigger, description, examples, steps, and body text.
  The menu shows only the matches.
- Workflow page: description, use when / avoid when, inputs and outputs, numbered steps with **Do** and
  **Done when**, checks and artifacts, links to its rules and skills, example requests, and the source path.
- Rule page: description, where it applies (`paths:` globs, or "manual" for `trigger: manual`), and the body.
- Skill page: description and the procedure body.
- The site never prints an empty section: a section without data is left out.
- Each page has a URL hash (`#workflow/devops/ci-cd/release-pipeline`, `#rule/<area>/<spec>/<name>`,
  `#skill/<area>/<spec>/<name>`), so links between pages work.
- Light and dark themes, with light as the default and the selected theme saved in the browser.

## Catalog format

`docs/site/catalog.json` follows `docs/catalog.schema.json` (version 1.4.0). Each entry of `areas` is one spec:
`area` (`<area>/<spec>`), `group`, `spec`, `summary`, `agents_path`, and the lists `rules`, `skills`, `workflows`.

- A rule has `name`, `description`, `paths`, `trigger`, `path`, `body`.
- A skill has `name`, `description`, `path`, `body`.
- A workflow has its frontmatter (`trigger`, `name`, `description`, `inputs`, `outputs`, `use_when`, `avoid_when`,
  `checks`, `artifacts`, `related_rules`, `uses_skills`), the resolved `rule_refs` and `skill_refs`
  (`{name, path}`; a rule or skill of the same spec first, then of the same area), `steps`
  (`{title, do, done_when}` from `### N. Title` blocks), `examples`, and `body`. `body` holds the raw markdown
  only when the steps cannot be parsed; otherwise it is empty.

`--validate` exits 1 when a workflow has fewer than 3 steps, a step lacks **Do** or **Done when**, a workflow names
an unknown rule or skill, a rule has no `description` or neither `paths:` nor `trigger: manual`, or a skill has no
`description`. `tests/content/test_docs_catalog.py` builds the catalog of the pack and renders every page with
`app.js` in Node (skipped without `node`) to check that no page has an empty section.

## GitHub Pages

The workflow `.github/workflows/docs-site.yml` runs on a push to `main` that changes `areas/**`, `docs/site/**`,
or the builder. It runs `build_docs_catalog.py --validate` and publishes `docs/site`.

## Examples

Examples come from the workflow itself: every body line `Example request: <text>` (or `**Example request:** <text>`)
becomes one entry in `examples`. `use_when` comes from `selection.use-when`, `avoid_when` from
`selection.avoid-when`. Prompt files are not read. `build_docs_catalog.py --require-examples` reports workflows
without such a line.
