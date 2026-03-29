---
name: {{kebab-case-workflow-name}}
type: workflow
trigger: /{{workflow-name}}
description: {{ONE_SENTENCE — what completing this workflow produces}}
inputs:
  - {{input_1 — name and description of required input}}
  - {{input_2}}
outputs:
  - {{output_1 — concrete deliverable, e.g. "signed-off implementation_plan.md"}}
  - {{output_2}}
roles:
  - {{role-1 — function name, e.g. "copywriter", "campaign-manager"}}
  - {{role-2}}
execution:
  initiator: {{role — must be one of: product-owner | pm | team-lead | developer | qa | designer}}
related-rules:
  - {{rule-filename.md}}
uses-skills:
  - {{skill-directory-name}}
quality-gates:
  - {{MEASURABLE_CRITERION_1 — checkable without human judgment}}
  - {{MEASURABLE_CRITERION_2}}
---

<!--
AGENT INSTRUCTIONS:
1. Fill all frontmatter fields. Missing fields cause the workflow to be skipped.
2. "trigger" must start with / and match the prompt filename exactly.
3. "roles" are who performs steps — use function names, not seniority titles.
4. "execution.initiator" must be one of the six standard roles.
5. "quality-gates" must be objectively checkable. "Looks good" is NOT a gate.
   Good gate: "All copy variants pass brand-voice rule 2 and score ≥ 70 on Flesch-Kincaid."
6. Every step MUST have: @role, Input, Actions (specific), Done when (checkable criterion).
7. Use imperative voice: "Create", "Check", "Verify", "Ask" — not "You should" or "Consider".
8. Include a failure path for at least one step.
9. Target: 60–200 lines total. Over 200 lines = split into two workflows.
10. Delete all AGENT INSTRUCTIONS comments before finalising.
-->

## Steps

### 1. {{STEP_NAME}} — `@{{role-1}}`

- **Input:** {{what arrives at this step — be specific}}
- **Actions:**

  {{SPECIFIC_ACTION_1 — include the actual command, query, template, or decision the agent should use}}

  {{SPECIFIC_ACTION_2}}

  > **If {{FAILURE_CONDITION}}:** {{EXPLICIT_FAILURE_PATH — what to do instead, not just "handle the error"}}

- **Done when:** {{CHECKABLE_CRITERION — e.g. "brief confirmed in writing", "all required fields in the template are non-empty"}}

---

### 2. {{STEP_NAME}} — `@{{role-1}}`

- **Input:** output of step 1
- **Actions:**

  {{ACTIONS}}

- **Done when:** {{CRITERION}}

---

### 3. {{STEP_NAME}} — `@{{role-2}}`

<!--
Steps involving a different role must state the handoff explicitly.
Example: "Receive draft from @developer. Review against architecture.md constraints."
-->

- **Input:** output of step 2
- **Actions:**

  {{ACTIONS}}

- **Done when:** {{CRITERION}}

---

### 4. {{STEP_NAME}} — `@{{role-1}}`

<!--
Add or remove steps as needed. Most workflows are 3–7 steps.
Fewer than 3 steps = write a skill instead.
More than 8 steps = split into two workflows.
-->

- **Input:** output of step 3
- **Actions:**

  {{ACTIONS}}

- **Done when:** {{CRITERION}}

---

## Exit

{{ONE_SENTENCE: when the workflow is complete and what was produced.}}
