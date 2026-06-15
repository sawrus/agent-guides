# Markdown docs site (search + menu)

This prototype renders a documentation site directly from markdown-derived catalog data.

## Why this stack

The user requirement was: site from markdown with search and menu. We evaluated popular GitHub projects:

- docsify: https://github.com/docsifyjs/docsify
- MkDocs: https://github.com/mkdocs/mkdocs
- Docusaurus: https://github.com/facebook/docusaurus
- markdown-it (parser): https://github.com/markdown-it/markdown-it

For this repo we keep it lightweight and dependency-minimal:

- catalog is generated offline by Python script from `areas/**/{workflows,prompts}`
- site is static HTML/CSS/JS
- markdown rendering via `marked` CDN
- full-text search via `lunr` CDN
- workflow diagrams rendered via `mermaid` CDN

## Run locally

```bash
make sync-diagrams
make build
python3 -m http.server 8000
# open http://localhost:8000/docs/site/
```

## Features

- Left menu grouped by area.
- Full-text search by trigger/name/description/examples.
- Language switcher: EN only / RU only / EN+RU.
- Light and dark themes, with light as the default and the selected theme saved in the browser.
- Workflow page with quality gates and source paths.
- Generated Mermaid agent interaction diagrams for workflows.


## GitHub Pages

This site can be published from GitHub Pages via Actions workflow (`.github/workflows/docs-site.yml`).


## Workflow mapping

Prompt-to-workflow mapping is command-based: `/workflow-file-name` in prompt text links to `workflows/<workflow-file-name>.md` in the same area.

## Workflow diagrams

Workflow diagrams are generated into `areas/**/workflows/*.md` between `agent-diagram` markers:

```bash
make sync-diagrams
```

The catalog builder extracts those Mermaid blocks into `workflow_diagram`, and the static site renders them after Markdown parsing.
