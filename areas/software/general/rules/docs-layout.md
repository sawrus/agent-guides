---
description: Keep docs/ in the root-design / feature / incident layout and cover every code change with a docs page.
paths:
  - "docs/**"
---

# Docs layout and coverage

- Put one root design page per whole artifact (service, tool, pipeline) at `docs/<artifact>.md`.
- Put feature work in `docs/<feature-slug>/README.md`; use a kebab-case slug, optionally prefixed by the ticket id.
- Put incidents in `docs/incidents/<YYYY-MM-DD>-<id>.md`.
- Add frontmatter `covers:` with code globs to every root design, feature, and incident page.
- When you change code, update in the same change at least one docs page whose `covers:` matches the changed path.
- If the change does not alter behaviour (tests, CI, refactoring, dependency bump), add the commit trailer
  `Docs-Not-Needed: <reason>` instead.
- Do not widen `covers:` to `**` to silence coverage; add a root design page for uncovered code.
- A feature page has: goal, numbered acceptance criteria, out of scope, contracts with examples, design and
  rejected alternative, risks and rollback, operability, status (`draft|agreed|implemented|superseded`).
- An incident page has: impact, root cause with evidence, fix with link and regression test, prevention actions.
- Describe behaviour and decisions; do not copy code into docs.
