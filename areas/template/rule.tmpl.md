# Rule: {{CONSTRAINT_DOMAIN_NAME}}

<!--
AGENT INSTRUCTIONS:
1. Replace {{CONSTRAINT_DOMAIN_NAME}} with a noun phrase describing what this rule constrains.
   Examples: "Brand Voice Standards", "Budget Approval Controls", "Data Privacy Requirements"
2. Set Priority to P0 or P1 (see definitions below).
3. Write every constraint as an imperative statement ("must", "never", "required", "forbidden").
4. Do NOT use "consider", "try", "ideally", "should" — these are advice, not rules.
5. Add 1+ compliant and 1+ non-compliant examples per constraint section.
6. Keep the entire file under 150 lines.
7. Delete all AGENT INSTRUCTIONS comments before finalising.
-->

**Priority**: {{P0_OR_P1}} — {{ONE_SENTENCE_ON_WHAT_NON_COMPLIANCE_CAUSES}}

<!--
P0 = Non-compliance blocks the task. Agent must refuse to proceed until resolved.
     Use for: legal risk, security violation, data loss, brand damage that requires immediate fix.
P1 = Non-compliance triggers a review flag. Agent continues but marks the item for human review.
     Use for: quality risk, process deviation, brand inconsistency that humans should assess.
-->

---

## {{SECTION_1_NAME}}

<!--
Group related constraints into sections. Each section should cover one coherent concern.
Example sections: "Tone and Voice", "Legal Disclaimers", "Visual Identity", "Approval Process"
-->

1. **{{CONSTRAINT_1_NAME}}**
   - {{SPECIFIC_REQUIREMENT_STATED_IMPERATIVELY}}
   - {{SUB_REQUIREMENT_OR_EXCEPTION_IF_ANY}}

2. **{{CONSTRAINT_2_NAME}}**
   - {{REQUIREMENT}}
   - Exception: {{EXCEPTION_CONDITION_IF_ANY}}

## {{SECTION_2_NAME}}

3. **{{CONSTRAINT_3_NAME}}**
   - {{REQUIREMENT}}

4. **{{CONSTRAINT_4_NAME}}**
   - {{REQUIREMENT}}

---

## Compliant examples

✅ {{REAL_EXAMPLE_OF_CORRECT_OUTPUT_OR_BEHAVIOR}}

✅ {{ANOTHER_COMPLIANT_EXAMPLE}}

## Non-compliant examples

❌ {{REAL_EXAMPLE_OF_VIOLATION}} — {{BRIEF_REASON_WHY_THIS_VIOLATES_THE_RULE}}

❌ {{ANOTHER_VIOLATION}} — {{REASON}}

---

<details>
<summary>Rationale</summary>

{{WHY_THIS_RULE_EXISTS}}

Regulatory/legal basis (if applicable): {{REGULATION_OR_POLICY_REFERENCE}}

Last reviewed: {{DATE_OR_LEAVE_BLANK}}
</details>
