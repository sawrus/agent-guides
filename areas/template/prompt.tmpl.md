---
workflow: {{workflow-name}}
---

# Prompt: `/{{command-name}}`

<!--
AGENT INSTRUCTIONS:
1. "workflow-name" and "command-name" must match the workflow file stem exactly (if a workflow exists for this command).
2. "Use when:" is ONE sentence describing the exact scenario. Not "Use when working in this spec."
3. Write 2–3 examples. Two is the minimum. Three is standard.
4. Every example MUST have both an EN block and an RU block.
5. EN and RU blocks must be SEMANTICALLY IDENTICAL — full translation, not paraphrase.
6. Examples must contain NO placeholders like [YOUR PRODUCT] or {{INSERT_URL}}.
7. Use realistic values: real tool names, realistic company/service names, realistic metrics.
8. EN block should be ≥ 200 words total across all fields to give the agent sufficient context.
9. Example 1 = most common / standard case.
   Example 2 = more complex, edge case, or different scenario.
   Example 3 (optional) = quick/minimal version or contrasting context.
10. Remove any legacy "Workflow link command:" section. The front matter is the mapping.
11. Delete all AGENT INSTRUCTIONS comments before finalising.
-->

Use when: {{SPECIFIC_SCENARIO_ONE_SENTENCE}}

---

## Example 1 — {{STANDARD_CASE_NAME}}

<!--
Standard case: the most common way this command is used.
A user should be able to copy this block and use it without any modification.
-->

**EN:**
```
/{{command-name}}

{{FIELD_1_LABEL}}: {{REALISTIC_VALUE}}
{{FIELD_2_LABEL}}: {{REALISTIC_VALUE}}
{{FIELD_3_LABEL}}: {{REALISTIC_VALUE}}
{{FIELD_4_LABEL}}: {{REALISTIC_VALUE}}

{{ADDITIONAL_CONTEXT_OR_CONSTRAINTS_OR_REQUIREMENTS}}

{{OUTPUT_SPECIFICATION — what exactly should be delivered, in what format, what length}}
```

**RU:**
```
/{{command-name}}

{{FIELD_1_LABEL_RU}}: {{REALISTIC_VALUE_RU}}
{{FIELD_2_LABEL_RU}}: {{REALISTIC_VALUE_RU}}
{{FIELD_3_LABEL_RU}}: {{REALISTIC_VALUE_RU}}
{{FIELD_4_LABEL_RU}}: {{REALISTIC_VALUE_RU}}

{{ADDITIONAL_CONTEXT_IN_RUSSIAN}}

{{OUTPUT_SPECIFICATION_IN_RUSSIAN}}
```

---

## Example 2 — {{COMPLEX_OR_EDGE_CASE_NAME}}

<!--
Complex case: shows a harder or different usage — more constraints, edge case, or demanding scenario.
Demonstrates the range of what this command can handle.
-->

**EN:**
```
/{{command-name}}

{{FIELD_1_LABEL}}: {{DIFFERENT_REALISTIC_VALUE}}
{{FIELD_2_LABEL}}: {{DIFFERENT_REALISTIC_VALUE}}
{{FIELD_3_LABEL}}: {{DIFFERENT_REALISTIC_VALUE}}

{{MORE_SPECIFIC_CONSTRAINTS_OR_CONTEXT}}

{{OUTPUT_SPECIFICATION}}
```

**RU:**
```
/{{command-name}}

{{FIELD_1_LABEL_RU}}: {{DIFFERENT_REALISTIC_VALUE_RU}}
{{FIELD_2_LABEL_RU}}: {{DIFFERENT_REALISTIC_VALUE_RU}}
{{FIELD_3_LABEL_RU}}: {{DIFFERENT_REALISTIC_VALUE_RU}}

{{MORE_SPECIFIC_CONSTRAINTS_IN_RUSSIAN}}

{{OUTPUT_SPECIFICATION_IN_RUSSIAN}}
```

---

## Example 3 — {{QUICK_OR_CONTRASTING_CASE_NAME}} *(optional)*

<!--
Optional third example. Use when there's a meaningfully different usage mode:
- A faster / minimal version of the command
- A contrasting domain context (B2B vs B2C, technical vs general audience)
- A specific tool integration variant
Remove this section entirely if you only need 2 examples.
-->

**EN:**
```
/{{command-name}}

{{CONTENT}}
```

**RU:**
```
/{{command-name}}

{{CONTENT_IN_RUSSIAN}}
```
