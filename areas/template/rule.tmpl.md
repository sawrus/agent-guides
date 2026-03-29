# Rule: {{CONSTRAINT_DOMAIN_NAME}}

<!--
AGENT INSTRUCTIONS:
1. Replace {{CONSTRAINT_DOMAIN_NAME}} with a noun phrase: "Brand Voice Standards", "Migration Safety Requirements".
2. Set Priority to P0 or P1 (see definitions below).
3. Write every constraint as imperative: "must", "never", "required", "forbidden".
4. Never use: "consider", "try", "ideally", "should" — these are advice, not rules.
5. Include at least 1 compliant and 1 non-compliant example per section.
6. Target: under 150 lines.
7. Delete all AGENT INSTRUCTIONS comments before finalising.
-->

**Priority**: {{P0_OR_P1}} — {{ONE_SENTENCE: what non-compliance causes}}

<!--
P0 = Non-compliance blocks the task. Agent must refuse to proceed until resolved.
     Use for: legal risk, security violation, data loss, brand damage requiring immediate fix.
P1 = Non-compliance triggers a review flag. Agent continues but marks the item for human review.
     Use for: quality risk, process deviation, inconsistency that humans should assess.
-->

---

## {{SECTION_1 — group related constraints under one coherent concern}}

<!--
Example section names: "Tone and Voice", "Legal Disclaimers", "Secret Handling", "Migration Safety"
-->

1. **{{CONSTRAINT_NAME}}**
   - {{SPECIFIC_REQUIREMENT — imperative statement}}
   - {{SUB_REQUIREMENT_OR_EXCEPTION_IF_ANY}}

2. **{{CONSTRAINT_NAME}}**
   - {{REQUIREMENT}}
   - Exception: {{EXCEPTION_CONDITION_IF_ANY}}

## {{SECTION_2}}

3. **{{CONSTRAINT_NAME}}**
   - {{REQUIREMENT}}

4. **{{CONSTRAINT_NAME}}**
   - {{REQUIREMENT}}

---

## Compliant examples

✅ {{REAL_EXAMPLE_OF_CORRECT_OUTPUT_OR_BEHAVIOR}}

✅ {{ANOTHER_COMPLIANT_EXAMPLE}}

## Non-compliant examples

❌ {{REAL_EXAMPLE_OF_VIOLATION}} — {{BRIEF_REASON}}

❌ {{ANOTHER_VIOLATION}} — {{REASON}}

---

<details>
<summary>Rationale</summary>

{{WHY_THIS_RULE_EXISTS — 2 to 4 sentences}}

Regulatory / legal basis (if applicable): {{REGULATION_OR_POLICY_REFERENCE}}

Last reviewed: {{DATE_OR_LEAVE_BLANK}}
</details>
