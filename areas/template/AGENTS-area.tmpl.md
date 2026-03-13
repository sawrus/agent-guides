# {{DOMAIN_NAME}} — area guidance index

<!--
AGENT INSTRUCTIONS:
This is the ROOT AGENTS.md for the entire area. It is loaded before any spec-level guidance.
It defines:
  1. What this area covers
  2. The load order (spec selection)
  3. Cross-cutting constraints that apply to ALL specs in this area
  4. The full spec map
Keep under 100 lines.
Delete all AGENT INSTRUCTIONS comments before finalising.
-->

## What this area covers

{{ONE_PARAGRAPH: what domain this area covers, who uses it, what kinds of work it guides agents through.}}

## Spec selection

When starting a task in this area, determine the relevant spec by matching the task to the spec that owns it:

| Task type | Spec to load |
|:---|:---|
| {{TASK_TYPE_1}} | `{{spec-name}}/` |
| {{TASK_TYPE_2}} | `{{spec-name}}/` |
| {{TASK_TYPE_3}} | `{{spec-name}}/` |
| {{TASK_TYPE_4}} | `{{spec-name}}/` |
| General / cross-cutting | `general/` (if present) |

If the task spans multiple specs, load the primary spec first, then the secondary spec's rules only (not skills/workflows).

## Cross-cutting constraints

<!--
Constraints that apply to ALL specs in this area, regardless of task type.
These are NOT duplicated in individual spec rule files.
-->

- **{{CROSS_CUTTING_CONSTRAINT_1}}** — {{one sentence, imperative}}
- **{{CROSS_CUTTING_CONSTRAINT_2}}** — {{one sentence, imperative}}
- **{{CROSS_CUTTING_CONSTRAINT_3}}** — {{one sentence, imperative}}

## Load order

1. This file (`areas/{{domain}}/AGENTS.md`)
2. Spec `AGENTS.md` (`areas/{{domain}}/{{spec}}/AGENTS.md`)
3. Spec `rules/*.md` (all rules for the selected spec)
4. Spec `skills/*/SKILL.md` (on-demand, matching "When to load")
5. Spec `workflows/*.md` (matching the slash command trigger)

## Specs in this area

```text
areas/{{domain}}/
├── {{spec-1}}/    # {{one_line_scope}}
├── {{spec-2}}/    # {{one_line_scope}}
├── {{spec-3}}/    # {{one_line_scope}}
├── {{spec-4}}/    # {{one_line_scope}}
├── {{spec-5}}/    # {{one_line_scope}}
├── {{spec-6}}/    # {{one_line_scope}}
├── {{spec-7}}/    # {{one_line_scope}}
└── {{spec-8}}/    # {{one_line_scope}}
```
