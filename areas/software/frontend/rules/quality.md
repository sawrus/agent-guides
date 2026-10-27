---
description: TypeScript, i18n, DOM access, and test requirements for frontend code.
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.vue"
  - "tsconfig*.json"
---

# Frontend code quality

- Set `"strict": true` in `tsconfig.json`.
- Do not use `any` without an `eslint-disable` comment that states the reason.
- Use i18n keys (`t('key.path')`) for every user-facing string.
- Do not call `document.getElementById` or `querySelector` inside components; use `useRef` or a template ref.
- Never mutate state objects in place; return a new object from every reducer or `setState` call.
- Add at least 1 rendering test and 1 interaction test for every new component.
- Remove `console.log` calls; use the project logger module.
