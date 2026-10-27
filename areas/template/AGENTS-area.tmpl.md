# {{DOMAIN_NAME}} — area index

<!--
AGENT INSTRUCTIONS:
This is the index of a whole area for contributors. It is not installed into projects.
List only specs and workflows that exist on disk. No roles, no report files, no cross-cutting essays.
Target: under 60 lines. Delete this comment before finalising.
-->

{{ONE_SENTENCE — what this area covers.}}

## Spec selection

| Task type | Spec |
|:---|:---|
| {{TASK_TYPE_1}} | `{{spec-name}}/` |
| {{TASK_TYPE_2}} | `{{spec-name}}/` |

## Load order

1. Spec `AGENTS.md` — installed into the project `AGENTS.md`.
2. Rules — loaded when a file matches `paths:`; `trigger: manual` rules when the task touches their topic.
3. Skills — on demand, when the description matches the task.
4. Workflows — when the request matches `selection.use-when` or the user types the trigger.

## Trigger registry

Triggers are unique across all areas.

| Trigger | Spec | Purpose |
|:---|:---|:---|
| `/{{workflow-name}}` | {{spec}} | {{one line}} |

## Specs in this area

```text
areas/{{domain}}/
├── {{spec-1}}/    # {{one_line_scope}}
└── {{spec-2}}/    # {{one_line_scope}}
```
