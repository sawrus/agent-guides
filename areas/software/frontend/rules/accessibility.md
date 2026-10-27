---
description: WCAG 2.1 AA constraints for web UI components in React, Vue, or plain HTML.
paths:
  - "**/*.tsx"
  - "**/*.jsx"
  - "**/*.vue"
  - "**/*.html"
---

# Accessibility

- Give every `button`, `a`, `input`, `select`, and custom widget an accessible name: visible text, `aria-label`, or `aria-labelledby`.
- Keep text contrast at 4.5:1 or more, and 3:1 or more for large text.
- Make every action work with the keyboard only (`Tab`, `Shift+Tab`, `Enter`, `Space`, arrow keys).
- Add a meaningful `alt` to every `img`; use `alt=""` for decorative images.
- Use an `aria-live` region or move focus to announce toasts, modal openings, and form errors.
- Do not set a `tabindex` value greater than `0`.
- Use native elements (`button`, `a href`) instead of a `div` with an `onClick` handler.
- Run `axe-core` or `eslint-plugin-jsx-a11y` on changed components; fail the check on any WCAG A or AA violation.
