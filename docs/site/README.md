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

- catalog is generated offline by Python script from `areas/**/workflows`
- site is static HTML/CSS/JS
- markdown rendering via `marked` CDN
- full-text search via `lunr` CDN

## Run locally

```bash
make build-docs
python3 -m http.server 8000
# open http://localhost:8000/docs/site/
```

## Features

- Compact expandable left menu grouped by top-level area and nested workflow section.
- Full-width trigger search under the install command, filtering by trigger/name/description/examples.
- Light and dark themes, with light as the default and the selected theme saved in the browser.
- Workflow page with quality gates and source paths.


## GitHub Pages

This site can be published from GitHub Pages via Actions workflow (`.github/workflows/docs-site.yml`).


## Examples

Examples come from the workflow itself: every body line `Example request: <text>` (or `**Example request:** <text>`)
becomes one entry in `examples`. `use_when` comes from `selection.use-when`. Prompt files are not read.
`build_docs_catalog.py --require-examples` reports workflows without such a line.

