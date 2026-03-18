---
name: {{kebab-case-workflow-name}}
type: workflow
trigger: /{{workflow-name}}
description: {{ONE_SENTENCE — what does completing this workflow produce?}}
inputs:
  - {{input_1 — name of the required input}}
  - {{input_2}}
outputs:
  - {{output_1 — concrete deliverable}}
  - {{output_2}}
roles:
  - {{role-1 — job title or function, e.g. "copywriter", "campaign-manager", "legal-reviewer"}}
  - {{role-2}}
execution:
  initiator: {{role-1 — must be one of: product-owner|pm|team-lead|developer|qa|designer}}
related-rules:
  - {{rule-filename.md}}
uses-skills:
  - {{skill-directory-name}}
  - {{skill-directory-name}}
quality-gates:
  - {{MEASURABLE_CRITERION_1 — checkable without human judgment, e.g. "all copy variants pass brand-voice rule 2"}}
  - {{MEASURABLE_CRITERION_2}}
---

<!--
AGENT INSTRUCTIONS:
1. Fill all frontmatter fields. Missing fields cause the workflow to be skipped by some agents.
2. "trigger" must start with / and match the prompt file name exactly.
3. "roles" are who performs the steps — not job levels. Use function names, not seniority (not "senior copywriter").
4. "execution.initiator" must be one of: `product-owner`, `pm`, `team-lead`, `developer`, `qa`, `designer`.
5. "quality-gates" must be checkable. "Looks good" is NOT a quality gate. "Draft passes all 5 headline criteria from headline-frameworks skill" IS.
6. Every step MUST have: @role, Input, Actions (specific), Done when (checkable).
7. Use imperative voice in steps: "Create", "Check", "Ask", "Verify" — not "You should" or "Consider".
8. Include failure paths for at least one step.
9. Target: 60–200 lines total. If > 200 lines, split into two workflows.
10. Delete all AGENT INSTRUCTIONS comments before finalising.
-->

## Steps

### 1. {{STEP_NAME}} — `@{{role-1}}`

- **Input:** {{what arrives at this step — be specific}}
- **Actions:**

  {{SPECIFIC_ACTION_1 — include the actual command, query, template, or decision the agent should use}}

  {{SPECIFIC_ACTION_2}}

  {{SPECIFIC_ACTION_3}}

  > **If {{FAILURE_CONDITION}}:** {{EXPLICIT_FAILURE_PATH — what to do instead}}

- **Done when:** {{CHECKABLE_CRITERION — e.g. "brief confirmed by stakeholder in writing", "all fields in the template are filled"}}

---

### 2. {{STEP_NAME}} — `@{{role-1}}`

- **Input:** {{output of step 1}}
- **Actions:**

  {{ACTIONS}}

- **Done when:** {{CRITERION}}

---

### 3. {{STEP_NAME}} — `@{{role-2}}`

<!--
Steps that involve a different role must clearly state the handoff.
Example: "Receive draft from @copywriter. Review against brand-voice-standards.md Rule 2."
-->

- **Input:** {{output of step 2}}
- **Actions:**

  {{ACTIONS}}

- **Done when:** {{CRITERION}}

---

### 4. {{STEP_NAME}} — `@{{role-1}}`

<!--
Add or remove steps as needed. Most workflows are 3–7 steps.
Fewer than 3 steps = not complex enough to need a workflow (write a skill instead).
More than 8 steps = split into two workflows.
-->

- **Input:** {{output of step 3}}
- **Actions:**

  {{ACTIONS}}

- **Done when:** {{CRITERION}}

---

## Exit

{{ONE_SENTENCE: when the workflow is complete and what was produced — e.g. "Workflow complete when all outputs are approved, published, and tracked in the campaign tracker."}}
