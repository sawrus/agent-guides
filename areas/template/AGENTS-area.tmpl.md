# {{DOMAIN_NAME}} — area guidance index

<!--
AGENT INSTRUCTIONS:
This is the ROOT AGENTS.md for the entire area.
Load it before any spec-level guidance.
It defines:
  1. What this area covers
  2. Spec selection (which spec to load for which task)
  3. Cross-cutting constraints applying to ALL specs in this area
  4. The full spec map
Target: under 100 lines.
Delete all AGENT INSTRUCTIONS comments before finalising.
-->

## What this area covers

{{ONE_PARAGRAPH: what domain this area covers, who uses it, what kinds of work it guides agents through.}}

## Spec selection

Match the task to the spec that owns it:

| Task type | Spec to load |
|:---|:---|
| {{TASK_TYPE_1}} | `{{spec-name}}/` |
| {{TASK_TYPE_2}} | `{{spec-name}}/` |
| {{TASK_TYPE_3}} | `{{spec-name}}/` |
| General / cross-cutting | `general/` (if present) |

If the task spans multiple specs, load the primary spec's full chain, then the secondary spec's `rules/*` only.

## Cross-cutting constraints

<!--
Constraints that apply to ALL specs in this area.
Not duplicated in individual spec rule files.
Write in imperative form.
-->

- **{{CONSTRAINT_1_NAME}}** — {{one sentence, imperative, e.g. "never commit secrets to source control."}}
- **{{CONSTRAINT_2_NAME}}** — {{one sentence, imperative}}
- **{{CONSTRAINT_3_NAME}}** — {{one sentence, imperative}}

## Load order

1. This file (`areas/{{domain}}/AGENTS.md`)
2. Spec `AGENTS.md` (`areas/{{domain}}/{{spec}}/AGENTS.md`)
3. Spec `rules/*.md` — all rules for the selected spec
4. Spec `skills/*/SKILL.md` — on-demand, matching "When to load"
5. Spec `workflows/*.md` — matching the slash command trigger

## Specs in this area

```text
areas/{{domain}}/
├── {{spec-1}}/    # {{one_line_scope}}
├── {{spec-2}}/    # {{one_line_scope}}
├── {{spec-3}}/    # {{one_line_scope}}
└── {{spec-4}}/    # {{one_line_scope}}
```
