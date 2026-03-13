# {{SPEC_NAME}} guidance index

<!--
AGENT INSTRUCTIONS:
This file is the entry point for agents working in this specialization.
It must be loaded FIRST before any rules, skills, or workflows.
Keep it under 80 lines — it is a navigation map, not a knowledge document.
Delete all AGENT INSTRUCTIONS comments before finalising.
-->

Use this map to load {{SPEC_NAME}}-specific guidance for {{ONE_LINE_SCOPE_DESCRIPTION}}.

## Guidance chain

Load in this order:

1. Project `.agent/` baseline guidance (`AGENTS.md` + `.agent/*`)
2. `{{domain}}/{{spec}}/rules/*` — always load all rules for this spec
3. `{{domain}}/{{spec}}/skills/*/SKILL.md` — load only the skill matching the current task (see "When to load" in each skill)
4. `{{domain}}/{{spec}}/workflows/*` — load the workflow matching the triggered slash command

## Inherited from {{DOMAIN_NAME}} area

<!--
List cross-cutting constraints that apply from the parent area's AGENTS.md or general/ spec.
These do NOT need to be repeated in this spec's rules.
-->

- {{INHERITED_CONSTRAINT_1 — e.g. "All content requires legal review before external publication"}}
- {{INHERITED_CONSTRAINT_2}}

## {{SPEC_NAME}}-specific overrides

<!--
List any constraints where this spec diverges from area-wide defaults.
-->

- {{OVERRIDE_1 — e.g. "Tone: formal in general area, but this spec uses conversational tone for B2C copy"}}

## File map

```text
{{spec-name}}/
├── rules/
{{#each rules}}│   ├── {{filename}}.md     ← {{one_line_description}}
{{/each}}├── skills/
{{#each skills}}│   ├── {{skill-dir}}/SKILL.md    ← {{one_line_description}}
{{/each}}├── workflows/
{{#each workflows}}│   ├── {{filename}}.md     ← /{{command}} — {{one_line_description}}
{{/each}}└── prompts/
{{#each prompts}}    ├── {{filename}}.md     ← /{{command}} — {{one_line_description}}
{{/each}}```

<!--
Replace the Handlebars-style blocks above with actual file names and descriptions.
Example for a copywriting spec:

├── rules/
│   ├── brand-voice-standards.md     ← P0: tone, vocabulary, persona requirements
│   ├── compliance-copy.md           ← P0: prohibited claims, disclaimer requirements
│   └── content-quality.md          ← P1: readability, structure, review criteria
├── skills/
│   ├── conversion-copywriting/SKILL.md    ← AIDA, PAS, FAB frameworks + real examples
│   ├── headline-frameworks/SKILL.md       ← 12 proven headline patterns with copy examples
│   └── seo-writing/SKILL.md              ← keyword integration without keyword stuffing
├── workflows/
│   ├── create-landing-page.md     ← /create-landing-page — full page copy end-to-end
│   └── review-copy.md             ← /review-copy — brand voice + conversion audit
└── prompts/
    ├── write-headline.md           ← /write-headline — 10 headline variants for A/B test
    └── rewrite-cta.md             ← /rewrite-cta — CTA optimisation for conversion
-->

## Discovery patterns

- `rules/*.md`
- `skills/*/SKILL.md`
- `workflows/*.md`
- `prompts/*.md`
