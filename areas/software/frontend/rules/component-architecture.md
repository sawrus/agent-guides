---
description: Component boundaries, file layout, and import rules for React or Vue frontends.
paths:
  - "**/*.tsx"
  - "**/*.jsx"
  - "**/*.vue"
---

# Component architecture

- Keep data fetching in page or container components; presentational components receive data through props.
- Do not pass a prop through more than 2 component levels; use context, a store, or composition instead.
- Put a component's styles, tests, and stories in the same directory as the component file.
- Keep data fetching and complex layout in separate components: a container and a presentational component.
- Put domain logic in hooks (`use*.ts`) or modules under `lib/`, not in JSX.
- Do not add circular imports; run the project's import-cycle check (for example `eslint-plugin-import` `no-cycle`) on changed modules.
- Put feature code under `src/features/<feature>/` and shared UI under `src/components/`.
- Document the loading, empty, error, and success states of every data-driven component in its story or test.
