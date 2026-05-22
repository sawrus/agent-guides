# {{SPEC_NAME}} — guidance index

<!--
AGENT INSTRUCTIONS:
This file is the entry point for agents working in this specialization.
Load it FIRST before any rules, skills, or workflows.
Target: under 80 lines — this is a navigation map, not a knowledge document.
Delete all AGENT INSTRUCTIONS comments before finalising.
-->

## What this area covers

{{ONE_PARAGRAPH: what domain this spec covers, who uses it, and what kinds of work it guides agents through.}}

## Inherited from {{DOMAIN_NAME}} area

<!--
List cross-cutting constraints that apply from the parent area's AGENTS.md.
These do NOT need to be repeated in this spec's rule files.
-->

- {{INHERITED_CONSTRAINT_1 — e.g. "All IaC changes must be version-controlled; no manual console edits."}}
- {{INHERITED_CONSTRAINT_2}}

## {{SPEC_NAME}}-specific constraints

<!--
List constraints where this spec diverges from or extends the area-wide defaults.
Write in imperative form: "must", "never", "required", "forbidden".
Avoid advice-language: "consider", "try to", "ideally".
-->

- {{CONSTRAINT_1 — e.g. "Every new service must expose the four golden signals before shipping."}}
- {{CONSTRAINT_2}}

## Spec map

```text
.agent/
├── rules/
│   ├── {{filename}}.md     ← {{one_line_description}}
│   └── {{filename}}.md     ← {{one_line_description}}
├── skills/
│   ├── {{skill-dir}}/SKILL.md    ← {{one_line_description}}
│   └── {{skill-dir}}/SKILL.md    ← {{one_line_description}}
├── workflows/
│   ├── {{filename}}.md     ← /{{command}} — {{one_line_description}}
│   └── {{filename}}.md     ← /{{command}} — {{one_line_description}}
└── prompts/
    └── *.md
```
