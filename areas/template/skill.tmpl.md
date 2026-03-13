---
name: {{kebab-case-skill-name}}
type: skill
description: {{ONE_SENTENCE_CAPABILITY_STATEMENT_STARTING_WITH_VERB — e.g. "Design and execute conversion-focused landing page copy."}}
related-rules:
  - {{rule-filename-1.md}}
  - {{rule-filename-2.md}}
allowed-tools: {{COMMA_SEPARATED_LIST — Read, Write, Edit, Bash, WebSearch}}
---

<!--
AGENT INSTRUCTIONS:
1. Fill all frontmatter fields before writing the body.
2. "name" must match the directory name exactly (e.g. if dir is "seo-keyword-research/", name is "seo-keyword-research").
3. "description" is one sentence, starts with a verb, says what the agent CAN DO after loading this skill.
4. "related-rules" lists rule files that constrain how this skill is applied.
5. "allowed-tools" lists only the tools actually needed — don't list Read/Write/Edit/Bash/WebSearch all if you don't need all of them.
6. Target: 150–350 lines total. Shorter = stub. Longer = split into two skills.
7. All examples must be REAL, not placeholders. See Section "Examples" below.
8. Delete all AGENT INSTRUCTIONS comments before finalising.
-->

# Skill: {{DISPLAY_NAME}}

> **Expertise:** {{COMMA_SEPARATED_LIST_OF_SPECIFIC_TECHNIQUES_TOOLS_OR_CONCEPTS_THIS_SKILL_COVERS}}

## When to load

<!--
This section is critical. The agent reads this to decide whether to load the skill.
Write precise triggers, not "when doing anything in this spec."
Bad: "When writing copy"
Good: "When writing a conversion-focused landing page with a specific CTA and a word count target"
-->

Load this skill when:
- {{SPECIFIC_TRIGGER_1 — describe the exact task condition that warrants loading this skill}}
- {{SPECIFIC_TRIGGER_2}}
- {{SPECIFIC_TRIGGER_3}}

Do NOT load for: {{WHAT_LOOKS_SIMILAR_BUT_DOES_NOT_NEED_THIS_SKILL}}

---

## {{MAIN_CONCEPT_OR_FRAMEWORK_SECTION_NAME}}

<!--
Explain the core technique, framework, or set of patterns this skill covers.
For creative domains: use named frameworks (AIDA, PAS, FAB) with real copy examples.
For technical domains: use runnable code/commands.
For process domains: use named methodologies with real document snippets.
-->

{{EXPLANATION_OF_THE_TECHNIQUE_OR_FRAMEWORK_IN_2_4_SENTENCES}}

### {{PATTERN_1_NAME}}

{{DESCRIPTION}}

```{{LANGUAGE_OR_REMOVE_CODE_FENCE_IF_NOT_CODE}}
{{REAL_WORKING_EXAMPLE}}
```

### {{PATTERN_2_NAME}}

{{DESCRIPTION}}

```{{LANGUAGE_OR_REMOVE_CODE_FENCE_IF_NOT_CODE}}
{{REAL_WORKING_EXAMPLE}}
```

### {{PATTERN_3_NAME}}

{{DESCRIPTION}}

---

## {{SECOND_TECHNIQUE_OR_TOOL_SECTION_NAME}}

<!--
Add a second section for a related technique, specific tool operations, or quality criteria.
Every skill should have at least 2 substantive sections.
-->

{{CONTENT}}

---

## {{OPTIONAL_THIRD_SECTION — e.g. "Quality Checklist", "Decision Framework", "Common Scenarios"}}

{{CONTENT}}

---

## Common mistakes

<!--
3–5 brief items. State the mistake, then the correction. Keep each under 2 sentences.
-->

1. **{{MISTAKE_1}}** — {{CORRECTION}}
2. **{{MISTAKE_2}}** — {{CORRECTION}}
3. **{{MISTAKE_3}}** — {{CORRECTION}}
4. **{{MISTAKE_4_OPTIONAL}}** — {{CORRECTION}}
5. **{{MISTAKE_5_OPTIONAL}}** — {{CORRECTION}}
