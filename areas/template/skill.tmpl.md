---
name: {{kebab-case-skill-name}}
type: skill
description: {{ONE_SENTENCE_STARTING_WITH_VERB — e.g. "Design and execute conversion-focused landing page copy."}}
related-rules:
  - {{rule-filename-1.md}}
  - {{rule-filename-2.md}}
allowed-tools: {{COMMA_SEPARATED — Read, Write, Edit, Bash, WebSearch}}
---

<!--
AGENT INSTRUCTIONS:
1. Fill all frontmatter fields before writing the body.
2. "name" must match the directory name exactly.
3. "description" starts with a verb; states what the agent CAN DO after loading this skill.
4. "related-rules" lists only the rule files that constrain how this skill is applied.
5. "allowed-tools" lists only tools actually needed — don't include all five by default.
6. Target: 150–350 lines total. Shorter = stub. Longer = split into two skills.
7. All examples must be REAL and runnable — no placeholders like [YOUR_VALUE].
8. Every skill needs at least 2 substantive sections and a "Common mistakes" section.
9. Delete all AGENT INSTRUCTIONS comments before finalising.
-->

# Skill: {{DISPLAY_NAME}}

> **Expertise:** {{COMMA_SEPARATED_LIST_OF_SPECIFIC_TECHNIQUES_TOOLS_OR_CONCEPTS}}

## When to load

<!--
Critical section — the agent reads this to decide whether to load the skill.
Write precise triggers. Vague triggers waste context.

Bad:  "When working in this spec."
Good: "When writing a new dbt model that joins more than two source tables and requires incremental materialization."
-->

Load this skill when:
- {{SPECIFIC_TRIGGER_1 — describe the exact task condition}}
- {{SPECIFIC_TRIGGER_2}}
- {{SPECIFIC_TRIGGER_3}}

Do NOT load for: {{WHAT_LOOKS_SIMILAR_BUT_DOES_NOT_NEED_THIS_SKILL}}

---

## {{MAIN_CONCEPT_OR_FRAMEWORK_SECTION}}

<!--
Explain the core technique, framework, or pattern set this skill covers.
For technical domains: use runnable code or commands.
For process domains: use named methodologies with real document snippets.
For creative domains: use named frameworks (AIDA, PAS) with real examples.
-->

{{EXPLANATION_IN_2_TO_4_SENTENCES}}

### {{PATTERN_OR_TECHNIQUE_1}}

{{DESCRIPTION}}

```{{language}}
{{REAL_WORKING_EXAMPLE — not a placeholder}}
```

### {{PATTERN_OR_TECHNIQUE_2}}

{{DESCRIPTION}}

```{{language}}
{{REAL_WORKING_EXAMPLE}}
```

### {{PATTERN_OR_TECHNIQUE_3}}

{{DESCRIPTION}}

---

## {{SECOND_TECHNIQUE_OR_TOOL_SECTION}}

<!--
Add a second section for a related technique, tool operations, quality criteria, or decision framework.
Every skill must have at least 2 substantive sections.
-->

{{CONTENT}}

---

## {{OPTIONAL_THIRD_SECTION — e.g. "Quality Checklist", "Decision Framework", "Common Scenarios"}}

{{CONTENT}}

---

## Common mistakes

<!--
3–5 items. State the mistake, then the correction. Keep each under 2 sentences.
Write from experience — what do agents (or humans) actually get wrong here?
-->

1. **{{MISTAKE_1}}** — {{CORRECTION}}
2. **{{MISTAKE_2}}** — {{CORRECTION}}
3. **{{MISTAKE_3}}** — {{CORRECTION}}
4. **{{MISTAKE_4_OPTIONAL}}** — {{CORRECTION}}
5. **{{MISTAKE_5_OPTIONAL}}** — {{CORRECTION}}
