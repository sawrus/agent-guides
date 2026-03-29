---
workflow: {{workflow-name}}
---

# Prompt: `/{{command-name}}`

<!--
AGENT INSTRUCTIONS:
1. "workflow-name" must match the workflow file stem exactly (if a workflow exists).
2. "Use when:" is ONE sentence describing the exact scenario.
3. Write 2–3 examples minimum. Example 1 = standard case. Example 2 = complex/edge case.
4. Every example MUST have both EN and RU blocks, semantically identical.
5. Examples must contain NO placeholders like [YOUR_PRODUCT] or {{INSERT_URL}}.
6. Use realistic values: real tool names, realistic metrics, realistic company names.
7. EN block should be ≥ 200 words total across all fields to give sufficient context.
8. Delete all AGENT INSTRUCTIONS comments before finalising.
-->

Use when: {{SPECIFIC_SCENARIO — one sentence, e.g. "setting up CI/CD for a new monorepo that uses pnpm workspaces and deploys to AWS ECS."}}

---

## Example 1 — {{STANDARD_CASE_NAME}}

**EN:**
```
/{{command-name}}

{{FIELD_1_LABEL}}: {{REALISTIC_VALUE}}
{{FIELD_2_LABEL}}: {{REALISTIC_VALUE}}
{{FIELD_3_LABEL}}: {{REALISTIC_VALUE}}

{{ADDITIONAL_CONTEXT — constraints, existing setup, non-goals}}

{{OUTPUT_SPECIFICATION — what exactly should be delivered, in what format}}
```

**RU:**
```
/{{command-name}}

{{FIELD_1_LABEL_RU}}: {{REALISTIC_VALUE_RU}}
{{FIELD_2_LABEL_RU}}: {{REALISTIC_VALUE_RU}}
{{FIELD_3_LABEL_RU}}: {{REALISTIC_VALUE_RU}}

{{ADDITIONAL_CONTEXT_RU}}

{{OUTPUT_SPECIFICATION_RU}}
```

---

## Example 2 — {{COMPLEX_OR_EDGE_CASE_NAME}}

**EN:**
```
/{{command-name}}

{{FIELD_1_LABEL}}: {{DIFFERENT_REALISTIC_VALUE}}
{{FIELD_2_LABEL}}: {{DIFFERENT_REALISTIC_VALUE}}

{{MORE_SPECIFIC_CONSTRAINTS_OR_CONTEXT}}

{{OUTPUT_SPECIFICATION}}
```

**RU:**
```
/{{command-name}}

{{FIELD_1_LABEL_RU}}: {{DIFFERENT_REALISTIC_VALUE_RU}}
{{FIELD_2_LABEL_RU}}: {{DIFFERENT_REALISTIC_VALUE_RU}}

{{MORE_SPECIFIC_CONSTRAINTS_RU}}

{{OUTPUT_SPECIFICATION_RU}}
```

---

## Example 3 — {{QUICK_OR_CONTRASTING_CASE}} *(optional)*

<!--
Use only when there is a meaningfully different usage mode:
a minimal/quick version, a contrasting domain context, or a specific tool variant.
Remove this section entirely if 2 examples are sufficient.
-->

**EN:**
```
/{{command-name}}

{{CONTENT}}
```

**RU:**
```
/{{command-name}}

{{CONTENT_RU}}
```
