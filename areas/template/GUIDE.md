# Area Build Guide — Interactive Playbook for AI Agents

> **AGENT INSTRUCTION — READ BEFORE ANYTHING ELSE**
>
> This is a **step-by-step playbook**, not a reference document. Do not read it once and immediately generate files.
> Follow each Phase in order. At the end of each Phase there is a **✅ Checkpoint** — only proceed when every box is ticked.
> If you skip a phase or a checkpoint item, the area you build will have gaps that are hard to fix later.
>
> **Compatible with:** Claude 3+, GPT-4o / o-series (Codex), Gemini 1.5+, Qwen2.5+, GLM-5, MiniMax 2.5, Llama 3.1+
> **Estimated build time:** 60–120 min for an area with 6–8 specializations, working at full generation speed.

---

## Table of Contents

- [Concepts: What Are Rules, Skills, Workflows, Prompts?](#concepts)
- [Phase 1 — Domain Analysis](#phase-1)
- [Phase 2 — Taxonomy Design](#phase-2)
- [Phase 3 — Scaffold Directory Structure](#phase-3)
- [Phase 4 — Build Rules](#phase-4)
- [Phase 5 — Build Skills](#phase-5)
- [Phase 6 — Build Workflows](#phase-6)
- [Phase 7 — Build Prompts](#phase-7)
- [Phase 8 — Quality Gate](#phase-8)
- [Appendix A — Artifact Anatomy (full spec)](#appendix-a)
- [Appendix B — Anti-Patterns](#appendix-b)
- [Appendix C — Domain Taxonomy Examples](#appendix-c)
- [Appendix D — Agent-Specific Notes](#appendix-d)

---

## Concepts: What Are Rules, Skills, Workflows, Prompts? {#concepts}

Before designing anything, internalize these four types. Every file you create belongs to exactly one type.

### Rule
A **constraint** the agent must always follow when working in this specialization.
- Loaded into context on every task in the spec.
- Short and opinionated — states what is required or forbidden, not why.
- Has a **Priority** (P0 = blocks work; P1 = triggers review).
- Never a best-practices essay. If it's longer than 150 lines, split it.

### Skill
A **capability guide** the agent loads when a specific task requires it.
- Loaded **on demand** when the task matches the skill's "When to load" condition.
- Contains real, runnable examples: code, commands, config, templates.
- Has YAML frontmatter declaring its dependencies and related rules.
- Aim for 150–350 lines. Shorter = stub. Longer = split into two skills.

### Workflow
A **step-by-step procedure** for a recurring, multi-step task.
- Triggered by a slash command (e.g. `/onboard-client`).
- Has defined inputs, outputs, roles (@role), and done-when criteria per step.
- The agent follows the steps in order; it is not a suggestion list.
- 60–200 lines depending on task complexity.

### Prompt
A **pre-written, domain-specific prompt** end-users copy-paste or type.
- One file = one slash command = 2–3 concrete usage examples.
- Each example is **bilingual** (EN block + RU block with identical content).
- Examples are specific: real tool names, real error messages, realistic service names.
- NOT generic placeholders. A user should be able to copy Example 1 and use it as-is.

---

## Phase 1 — Domain Analysis {#phase-1}

> **Goal:** Understand the domain deeply enough to make correct taxonomy decisions.
> Do NOT design specializations yet. Just gather facts.

### 1.1 Answer these questions (write your answers in a scratch block)

```
DOMAIN: [what area are you building — e.g. "marketing", "legal", "finance"]

1. Who are the practitioners?
   (Job titles, team names — e.g. "copywriter, SEO specialist, campaign manager")

2. What are the core recurring activities they perform?
   (List 10–15 activities — e.g. "write landing page copy", "run A/B test", "audit keyword rank")

3. What are the primary tools/platforms in this domain?
   (e.g. "HubSpot, Figma, Ahrefs, Meta Ads Manager, Notion")

4. What does a "production incident" look like?
   (What breaks badly? e.g. "campaign spend blows past budget", "compliance violation in ad copy")

5. What are the hardest decisions practitioners face?
   (e.g. "channel mix allocation", "tone vs conversion trade-off")

6. What does "done" look like for the main deliverables?
   (e.g. "approved copy with brand sign-off", "campaign live with tracking configured")

7. What rules/constraints are non-negotiable in this domain?
   (Regulatory, brand, technical — e.g. "no unsubstantiated claims", "GDPR consent required")
```

### 1.2 Identify tool clusters

Group the tools you listed by which type of practitioner uses them:

```
Tool cluster A: [tools used by role A]
Tool cluster B: [tools used by role B]
...
```

Each distinct tool cluster is a candidate specialization.

### 1.3 Identify activity clusters

Group the activities you listed into 5–10 coherent clusters where:
- Each cluster = work one person could reasonably own
- Clusters have minimal overlap
- Clusters together cover the full domain

```
Activity cluster 1: [name] — covers activities: [x, y, z]
Activity cluster 2: [name] — covers activities: [a, b, c]
...
```

### ✅ Phase 1 Checkpoint

- [ ] Domain name decided
- [ ] 10+ activities listed
- [ ] 5+ tools listed
- [ ] "Production incident" defined
- [ ] 5–10 activity clusters identified
- [ ] Tool clusters mapped to activity clusters

---

## Phase 2 — Taxonomy Design {#phase-2}

> **Goal:** Define the exact set of specializations (specs) for this area.
> Target: **6–9 specs**. Fewer = under-specified. More = overlap and bloat.

### 2.1 Map clusters to specializations

For each activity cluster from Phase 1, decide:
- Is it big enough to be its own spec? (≥ 3 distinct workflows, ≥ 3 distinct skills)
- Or should it merge with an adjacent cluster?

Name each spec using a **noun or noun-phrase** that matches a real job role or team:
✅ Good: `seo`, `paid-media`, `content-strategy`, `email-marketing`, `brand-voice`
❌ Bad: `writing-stuff`, `ads-things`, `misc-marketing`

### 2.2 Validate each spec against this checklist

For each candidate spec, confirm:

```
Spec: [name]
  [ ] Has 3–5 distinct, recurring workflows (tasks people do regularly)
  [ ] Has 3–6 distinct skills (bodies of knowledge/technique that can be learned)
  [ ] Has 2–4 hard rules/constraints that a practitioner must always follow
  [ ] Has a clear "owner" — one role or one person could own this entire spec
  [ ] Does NOT heavily overlap with an adjacent spec (< 20% shared activities)
```

If a spec fails 2+ checks: merge it with the closest neighbor.
If a spec would have 10+ workflows: split it into two specs.

### 2.3 Define the lifecycle axis

Every area has a **central lifecycle** — the sequence of stages work flows through. Map each spec to the stage(s) it owns:

```
Domain lifecycle: [Stage 1] → [Stage 2] → [Stage 3] → ... → [Stage N]
                   ↑            ↑            ↑
                [spec-a]    [spec-b]     [spec-c, spec-d]
```

Example (marketing):
```
Lifecycle: Strategy → Content Creation → Distribution → Paid Amplification → Analytics → Optimization
             ↑              ↑                 ↑               ↑                  ↑
        [brand-voice]  [copywriting]     [seo,email]    [paid-media]         [analytics]
```

This lifecycle will become the Coverage Matrix dimension in your scorecard.

### 2.4 Write the final taxonomy

```
areas/[domain]/
├── [spec-1]/    # [one-line description]
├── [spec-2]/    # [one-line description]
├── [spec-3]/    # [one-line description]
...
└── [spec-N]/    # [one-line description]
```

### ✅ Phase 2 Checkpoint

- [ ] 6–9 specs defined
- [ ] Every spec passes the 5-item validation checklist
- [ ] Lifecycle axis drawn, all specs mapped
- [ ] No two specs share > 20% of activities
- [ ] Each spec has a clear single-role owner
- [ ] Taxonomy written in directory tree format

---

## Phase 3 — Scaffold Directory Structure {#phase-3}

> **Goal:** Create all empty directories and stub files before filling content.
> Working top-down prevents orphaned files and makes coverage gaps visible.

### 3.1 Create the area root files

```
areas/[domain]/
├── AGENTS.md          ← area-level guidance index (load order, inheritance)
└── README.md          ← human-readable overview of what this area covers
```

Use `AGENTS.tmpl.md` and `README.tmpl.md` from this templates directory.

### 3.2 For each spec, create this structure

```
areas/[domain]/[spec]/
├── AGENTS.md          ← spec-level guidance index
├── README.md          ← what this spec covers, who it's for
├── PROMPTS.md         ← slash command index table
├── rules/
│   ├── [rule-1].md
│   ├── [rule-2].md
│   └── [rule-3].md
├── skills/
│   ├── [skill-1]/SKILL.md
│   ├── [skill-2]/SKILL.md
│   └── [skill-3]/SKILL.md
├── workflows/
│   ├── [workflow-1].md
│   └── [workflow-2].md
└── prompts/
    ├── [prompt-1].md
    └── [prompt-2].md
```

### 3.3 Name files correctly

**Rules** — kebab-case noun phrases describing the constraint domain:
`brand-voice-standards.md`, `compliance-review.md`, `budget-controls.md`

**Skills** — kebab-case, match the capability name used in the "When to load" trigger:
`seo-keyword-research/SKILL.md`, `ad-copy-framework/SKILL.md`

**Workflows** — verb-noun, matches the slash command without the slash:
`onboard-client.md` → `/onboard-client`, `audit-campaign.md` → `/audit-campaign`

**Prompts** — same as workflow trigger name; one prompt file = one slash command:
`write-landing-page.md` → `/write-landing-page`

### ✅ Phase 3 Checkpoint

- [ ] Area root AGENTS.md and README.md created
- [ ] All spec directories created
- [ ] Each spec has rules/, skills/, workflows/, prompts/ subdirectories
- [ ] Each spec has AGENTS.md, README.md, PROMPTS.md
- [ ] All planned files listed (even if empty) so gaps are visible

---

## Phase 4 — Build Rules {#phase-4}

> **Goal:** Write 3–4 rules per spec. Each rule is a hard constraint, not advice.
> Build rules FIRST — they define the boundaries that skills and workflows operate within.

### 4.1 For each spec, identify rule candidates

Ask: "What would a senior practitioner in this spec consider a **non-negotiable**?"
- Legal/regulatory constraints (must-follow by law or policy)
- Brand/quality constraints (must-follow for consistency)
- Technical constraints (must-follow for system integrity)
- Process constraints (must-follow for team coordination)

### 4.2 Assign priority to each rule

| Priority | Meaning | Effect |
|:---|:---|:---|
| **P0** | Blocks work. Non-compliance stops the task. | Agent refuses to proceed until resolved. |
| **P1** | Triggers review. Work continues but flags required. | Agent adds a review note and continues. |

> Rule of thumb: P0 = legal/security/data risk. P1 = brand/quality/process risk.

### 4.3 Write each rule using `rule.tmpl.md`

The rule template enforces:
1. Priority declaration at the top
2. Numbered, imperative statements ("Do X", "Never Y", "Always Z")
3. Concrete examples of compliant vs non-compliant content
4. Rationale in a collapsible block (not in the main body)

### 4.4 Rules quality bar

Before finishing each rule:
- [ ] Under 150 lines
- [ ] Priority (P0/P1) declared in first 3 lines
- [ ] Every statement is a constraint, not advice ("must", "never", "required" — not "consider", "try", "ideally")
- [ ] At least 1 concrete compliant example and 1 non-compliant example
- [ ] No overlap with rules in other specs of the same area

### ✅ Phase 4 Checkpoint (per spec)

- [ ] 3–4 rules written for this spec
- [ ] Every rule has a priority
- [ ] Every rule passes the 4-item quality bar
- [ ] Rules collectively cover: at least 1 legal/compliance constraint + 1 quality/brand constraint

---

## Phase 5 — Build Skills {#phase-5}

> **Goal:** Write 4–6 skills per spec. Each skill is a concrete how-to reference with working examples.
> Skills are the primary vehicle for technical depth — don't be vague here.

### 5.1 For each spec, identify skill candidates

Ask: "What would a new hire need to **study** to become effective in this spec?"
Each answer is a skill. A skill is distinct from a workflow in that:
- A skill = a body of knowledge/technique (reusable across many tasks)
- A workflow = a specific procedure for a specific recurring task

Good skill topics:
- A technique with multiple patterns/variants (e.g. `headline-frameworks`, `seo-keyword-research`)
- A tool's main operations (e.g. `meta-ads-manager`, `google-analytics-4`)
- A methodology the team follows (e.g. `conversion-copywriting`, `jtbd-analysis`)

### 5.2 Write the YAML frontmatter first

Before writing the body, declare:
```yaml
---
name: [skill-name]
type: skill
description: [one sentence — what does this skill enable the agent to do?]
related-rules:
  - [rule-file-that-constrains-this-skill].md
allowed-tools: [Read, Write, Edit, Bash, WebSearch — which tools can the agent use]
---
```

### 5.3 Write the "When to load" section

This is the most important part of the skill. The agent uses this to decide whether to load the skill at all.

Format:
```markdown
## When to load

Load this skill when:
- [specific task trigger 1]
- [specific task trigger 2]
- [specific task trigger 3]

Do NOT load for: [what looks similar but doesn't need this skill]
```

Be precise. "When writing copy" is too broad. "When writing conversion-focused landing page copy" is correct.

### 5.4 Write the skill body with real examples

Each skill body must contain:
1. **Concept explanation** — what is this technique/tool? (2–4 sentences)
2. **Patterns / frameworks** — the main approaches, numbered or as subsections
3. **Working examples** — real output the agent can generate or adapt
4. **Common mistakes** — 3–5 things practitioners get wrong (brief)

**For technical domains (devops, data, backend):** include runnable code/commands.
**For creative domains (marketing, copywriting, design):** include real copy/content examples, not placeholders.
**For process domains (legal, finance, PM):** include real document snippets or decision frameworks.

### 5.5 Skills quality bar

- [ ] 150–350 lines
- [ ] YAML frontmatter complete
- [ ] "When to load" is precise (not "when doing anything in this spec")
- [ ] At least 2 working examples (not `[YOUR CONTENT HERE]` placeholders)
- [ ] Common mistakes section present
- [ ] Mentions at least 1 related rule from the spec's rules/

### ✅ Phase 5 Checkpoint (per spec)

- [ ] 4–6 skills written
- [ ] Every skill has "When to load" with 3+ specific triggers
- [ ] Every skill has 2+ real examples
- [ ] Skills cover: at least 1 foundational technique + 1 tool-specific skill + 1 quality/review skill

---

## Phase 6 — Build Workflows {#phase-6}

> **Goal:** Write 2–4 workflows per spec. Each workflow is a complete, executable procedure.
> Workflows are triggered by slash commands. The agent executes them step by step.

### 6.1 For each spec, identify workflow candidates

A workflow is warranted when:
- The task happens **regularly** (at least monthly)
- The task has **3+ distinct steps** that must happen in order
- The task involves **multiple decisions** or **multiple roles**
- Getting the task wrong has **meaningful consequences**

Common workflow patterns across domains:
- `onboard-[entity]` — first-time setup of something new
- `audit-[entity]` — systematic review and assessment
- `debug-[problem]` — diagnose and fix a recurring class of problem
- `create-[deliverable]` — end-to-end creation of a key artifact
- `review-[entity]` — quality review before publish/launch/submit

### 6.2 Write the YAML frontmatter

```yaml
---
name: [workflow-name]
type: workflow
trigger: /[workflow-name]
description: [one sentence — what does this workflow accomplish?]
inputs:
  - [required input 1]
  - [required input 2]
outputs:
  - [concrete deliverable 1]
  - [concrete deliverable 2]
roles:
  - [role-1]
  - [role-2]
related-rules:
  - [rule-file].md
uses-skills:
  - [skill-name]
quality-gates:
  - [measurable completion criterion 1]
  - [measurable completion criterion 2]
---
```

### 6.3 Write steps following this pattern

Each step must have:
```markdown
### [N]. [Step Name] — `@[role]`
- **Input:** what this step receives
- **Actions:**
  [specific actions, commands, decisions — with real examples]
- **Done when:** [measurable criterion — not "when complete"]
```

Rules for steps:
- Use imperative voice ("Create X", "Check Y", "Ask Z")
- Include the actual command/query/prompt the agent should use — not "run the appropriate command"
- Every step has a **done when** condition that is checkable without human judgment
- If a step can fail, include the failure path explicitly

### 6.4 Workflows quality bar

- [ ] 60–200 lines
- [ ] YAML frontmatter with all fields
- [ ] Every step has @role, input, actions, done-when
- [ ] quality-gates are measurable (not "looks good", "seems complete")
- [ ] Failure paths documented for at least 1 step
- [ ] Workflow uses at least 1 skill from the spec's skills/

### ✅ Phase 6 Checkpoint (per spec)

- [ ] 2–4 workflows written
- [ ] Every workflow is triggered by a slash command
- [ ] Workflows collectively cover: at least 1 creation workflow + 1 review/audit workflow
- [ ] No workflow is just a checklist without @role assignments

---

## Phase 7 — Build Prompts {#phase-7}

> **Goal:** Write 5 prompt files per spec. These are the end-user's entry points.
> Prompts must be specific enough that a user can copy Example 1 and use it without modification.

### 7.1 Identify the 5 slash commands for each spec

Choose 5 tasks that:
- Are frequent (end-users will need these regularly)
- Are specific enough to have a single clear output
- Benefit from structured input (not just "write me copy")
- Together cover the spec's most important activities

Name format: `/verb-noun` — and where a workflow exists, the prompt file name, front matter key, header command, and workflow trigger must all match the workflow file stem exactly.

### 7.2 Write each prompt file using `prompt.tmpl.md`

Structure of each prompt file:
```markdown
---
workflow: [workflow-file-stem]
---

# Prompt: `/[command]`

Use when: [exact scenario — one sentence]

---

## Example 1 — [Standard case name]

**EN:**
```
/[command]

[structured input block with real values]
```

**RU:**
```
/[command]

[identical content in Russian]
```

---

## Example 2 — [Complex/edge case name]

...

## Example 3 — [Quick/minimal case name] (optional)
...
```

### 7.3 Rules for writing good examples

**Specificity requirements:**
- Use real tool/platform names (not `[YOUR TOOL]`)
- Use realistic entity names (not `example-service`, `my-company`)
- Include real metrics, real error messages, real constraints
- The "Standard case" example should represent the most common usage
- The "Complex case" example should show the edge case or most demanding usage

**Bilingual requirement:**
- EN and RU blocks must be semantically identical
- Translate fully — do not leave English fragments in the RU block
- Terminology: use the Russian professional term where one exists; use transliteration otherwise (e.g. "лендинг", "сплит-тест", "хедлайн")

**Avoid:**
- Generic placeholders: `[PRODUCT NAME]`, `[INSERT URL]`
- Vague outputs: "write good copy", "analyze the data"
- Missing constraints: always include scope, format, tone, length target, or tool context
- Single-language files

### 7.4 Prompts quality bar

- [ ] 2–3 examples per file (not 1, not 4+)
- [ ] Front matter includes `workflow: <workflow-stem>`
- [ ] Prompt filename matches the workflow stem
- [ ] Both EN and RU blocks in every example
- [ ] EN block ≥ 200 words (enough context for the agent to act without follow-up)
- [ ] No `[PLACEHOLDER]` strings remain
- [ ] No legacy `Workflow link command:` section remains
- [ ] Example 1 is immediately usable without modification
- [ ] "Use when:" line is specific (not "Use when: working in this spec")

### 7.5 Write the PROMPTS.md index

After all prompts are written, create the spec's `PROMPTS.md`:

```markdown
# PROMPTS: [spec-name]

| Prompt | Use when |
|:---|:---|
| `/[command-1]` | [one-line trigger description] |
| `/[command-2]` | [one-line trigger description] |
...
```

### ✅ Phase 7 Checkpoint (per spec)

- [ ] 5 prompt files written
- [ ] Every file has 2–3 examples
- [ ] Every example is bilingual (EN + RU)
- [ ] No placeholders in any example
- [ ] PROMPTS.md index created and matches actual files

---

## Phase 8 — Quality Gate {#phase-8}

> **Goal:** Verify the entire area before marking it complete.
> Run this phase once after ALL specs are built.

### 8.1 Completeness matrix

For each spec, fill in this table:

```
Spec        | Rules | Skills | Workflows | Prompts | AGENTS.md | README.md | PROMPTS.md
[spec-1]    |  3/3  |  5/5   |   3/3     |  5/5    |    ✅     |    ✅     |    ✅
[spec-2]    |       |        |           |         |           |           |
...
```

Target minimums:
- Rules: **3** (≥ 1 P0)
- Skills: **4** (≥ 1 tool-specific, ≥ 1 foundational)
- Workflows: **2** (≥ 1 creation, ≥ 1 review/audit)
- Prompts: **5** (5 × bilingual EN+RU)

### 8.2 Coverage audit — lifecycle axis

Map each workflow to the lifecycle stages from Phase 2:

```
Lifecycle stage | Covered by spec | Covered by workflow
[Stage 1]       | [spec-name]     | /[workflow]
[Stage 2]       | [spec-name]     | /[workflow]
...
[Stage N]       | ❌ UNCOVERED    |
```

Any lifecycle stage with no workflow coverage is a gap. Add a workflow or accept the gap explicitly.

### 8.3 Cross-spec duplication check

For each pair of adjacent specs:
- [ ] No rule appears (nearly) verbatim in two specs → if it does, move it to a shared `general/` spec
- [ ] No skill covers the same technique from the same angle → if it does, keep only the more specific one and reference it
- [ ] No two prompt commands do the same task → if they do, merge or differentiate

### 8.4 Token budget check

For each spec, estimate the always-on token load:
- Sum of lines in `rules/*.md` × ~4 tokens/line
- AGENTS.md overhead: ~100 tokens

Target: always-on load ≤ 1,500 tokens per spec (rules only).
Skills are loaded on-demand and do not count toward always-on budget.

If a rule file exceeds 150 lines: split it.
If total rules for a spec exceed 500 lines: you have too many rules — consolidate.

### 8.5 Final file audit

```bash
# Run this to see the full file tree:
find areas/[domain] -type f | sort

# Check for any files < 30 lines (likely stubs):
find areas/[domain] -name "*.md" | xargs wc -l | sort -n | head -20
```

Fix any file < 30 lines — it's a stub and will confuse agents.

### ✅ Phase 8 Checkpoint

- [ ] Completeness matrix filled — all minimums met
- [ ] Lifecycle coverage audit complete — all gaps documented
- [ ] No verbatim rule duplication across specs
- [ ] No spec has always-on token load > 1,500 tokens
- [ ] No file < 30 lines remains
- [ ] AGENTS.md at area root correctly lists all specs and their guidance chain

---

## Appendix A — Artifact Anatomy {#appendix-a}

### A.1 Rule anatomy

```markdown
# Rule: [Constraint Domain Name]

**Priority**: [P0 / P1] — [one sentence on what non-compliance causes]

## [Section 1: main constraint cluster]

1. **[Constraint name]**
   - [Specific requirement, stated imperatively]
   - [Sub-requirement or exception]

2. **[Constraint name]**
   - [Requirement]

## [Section 2]

3. **[Constraint name]**
   ...

## Compliant examples

✅ [Real example of correct behavior/output]
✅ [Another compliant example]

## Non-compliant examples

❌ [Real example of violation] — [brief reason]
❌ [Another violation]

<details>
<summary>Rationale</summary>
[Why this rule exists — regulatory, brand, technical reason. Keep brief.]
</details>
```

### A.2 Skill anatomy

```markdown
---
name: [kebab-case-name]
type: skill
description: [one sentence capability statement]
related-rules:
  - [rule.md]
allowed-tools: [Read, Write, Edit, Bash, WebSearch]
---

# Skill: [Display Name]

> **Expertise:** [comma-separated list of specific techniques/tools this skill covers]

## When to load

Load this skill when:
- [precise trigger 1]
- [precise trigger 2]

Do NOT load for: [what to avoid loading this for]

## [Main framework / technique section]

[explanation + pattern list]

```[language]
[real working example]
```

## [Second technique or tool section]

...

## Common mistakes

1. [Mistake] — [brief correction]
2. [Mistake] — [brief correction]
3. [Mistake] — [brief correction]
```

### A.3 Workflow anatomy

```markdown
---
name: [kebab-case]
type: workflow
trigger: /[command]
description: [one sentence]
inputs:
  - [input_name]
outputs:
  - [output_name]
roles:
  - [role-1]
quality-gates:
  - [measurable criterion]
---

## Steps

### 1. [Step Name] — `@[role]`
- **Input:** [what arrives]
- **Actions:**
  [specific instructions with examples]
- **Done when:** [checkable criterion]

### 2. [Step Name] — `@[role]`
...

## Exit
[One sentence: when the workflow is complete and what was produced]
```

### A.4 Prompt anatomy

```markdown
# Prompt: `/[command]`

Use when: [specific scenario]

---

## Example 1 — [Case name]

**EN:**
```
/[command]

[structured input with real values, ≥ 200 words total across all fields]
```

**RU:**
```
/[command]

[identical content in Russian]
```

---

## Example 2 — [Case name]

**EN:**
```
...
```

**RU:**
```
...
```
```

---

## Appendix B — Anti-Patterns {#appendix-b}

These are mistakes discovered during real area builds. Avoid all of them.

### B.1 The Stub (most common)

**What it looks like:**
```markdown
# Skill: SEO Research

This skill covers SEO keyword research.

## TODO
- Add examples
- Add patterns
```

**Why it's harmful:** An agent that loads a stub skill has no useful information and will hallucinate its own technique.
**Fix:** Never create a file without completing it. If you run out of time, do NOT create the file at all — an absent file is better than a stub.

### B.2 The Advice Rule

**What it looks like:**
```markdown
# Rule: Copy Quality

Consider using clear, concise language. Try to address the reader directly.
Ideally, use active voice. Think about your audience.
```

**Why it's harmful:** "Consider", "try", "ideally" are not constraints. The agent will not enforce them.
**Fix:** Every sentence in a rule must use "must", "required", "forbidden", "never", or "always".

### B.3 The Placeholder Prompt

**What it looks like:**
```markdown
## Example 1 — Standard case

**EN:**
```
/write-copy

Product: [YOUR PRODUCT]
Audience: [YOUR AUDIENCE]
Tone: [YOUR TONE]
```
```

**Why it's harmful:** This is useless. Users will not know what to put in the brackets, and the agent receives no domain signal.
**Fix:** Write a fully fleshed example with realistic values. Users adapt it — they do not fill templates.

### B.4 The Bloated Rule File

**What it looks like:** A single rule file with 400+ lines covering everything in the spec.

**Why it's harmful:** Rules are always-on context. A 400-line rule file costs ~1,600 tokens on every task, even simple ones. It also becomes hard to reason about.
**Fix:** Max 150 lines per rule file. Split by constraint domain (e.g. separate files for `brand-voice.md`, `compliance.md`, `budget-controls.md`).

### B.5 The Missing "When to load"

**What it looks like:** A skill that just starts with the technique, no loading instruction.

**Why it's harmful:** The agent can't decide whether to load the skill. It either loads everything (token waste) or nothing (capability miss).
**Fix:** Every skill's first section after frontmatter must be "When to load" with 3+ specific triggers.

### B.6 Taxonomy Too Flat

**What it looks like:** An area with 2–3 massive specs that each have 12+ workflows.

**Why it's harmful:** No practitioner owns a spec with 12 workflows. The agent can't specialize. Token budget explodes.
**Fix:** Split large specs. Each spec should represent ~one team member's expertise area.

### B.7 Taxonomy Too Deep

**What it looks like:** 15+ specs with 1–2 workflows each.

**Why it's harmful:** The area becomes hard to navigate. Adjacent specs overlap heavily. The agent has no clear primary spec to load.
**Fix:** Merge specs that share > 50% of their workflows and tools.

### B.8 English-Only Prompts

**What it looks like:** Prompts with EN examples but no RU block.

**Why it's harmful:** Excludes Russian-speaking users from the primary entry point of the system.
**Fix:** Every prompt example must have both EN and RU blocks. Translate fully — including all technical context, not just the prose.

### B.9 Workflow Without Done-When

**What it looks like:**
```markdown
### 3. Review Copy
- Read through the draft
- Make any necessary changes
```

**Why it's harmful:** The agent (or human) doesn't know when to stop. "Necessary changes" is undefined.
**Fix:** Every step ends with "Done when: [specific, checkable criterion]". Example: "Done when: draft passes all 5 brand voice criteria from brand-voice.md Rule 3."

### B.10 Orphaned Files

**What it looks like:** A skill file that no workflow references and no AGENTS.md mentions.

**Why it's harmful:** The agent never loads it. It's dead weight.
**Fix:** Every skill must be referenced in at least one workflow's `uses-skills:` frontmatter, OR in the spec's AGENTS.md guidance chain.

---

## Appendix C — Domain Taxonomy Examples {#appendix-c}

These are example taxonomies for common non-technical domains. Use them as starting points — adapt to your specific organizational context.

### C.1 Marketing

```
areas/marketing/
├── brand-strategy/      # Brand positioning, voice, identity system
├── content-marketing/   # Blog, long-form, thought leadership
├── copywriting/         # Conversion copy, landing pages, ads, email
├── seo/                 # Keyword research, on-page, technical, link
├── paid-media/          # Meta Ads, Google Ads, programmatic
├── email-marketing/     # Campaigns, automations, list hygiene
├── social-media/        # Organic social, community, creator partnerships
└── analytics/           # Attribution, reporting, experimentation
```

Lifecycle: Brand → Content → SEO → Paid → Email → Social → Analytics

### C.2 Legal

```
areas/legal/
├── contract-review/     # Review, redline, negotiation of agreements
├── compliance/          # Regulatory tracking, policy, audit response
├── ip-management/       # Trademark, copyright, patent, licensing
├── data-privacy/        # GDPR, CCPA, DPA, privacy reviews
├── litigation/          # Dispute management, e-discovery, filings
└── corporate-governance/# Board docs, cap table, equity, M&A prep
```

Lifecycle: Governance → Contracts → IP → Privacy/Compliance → Disputes

### C.3 Finance

```
areas/finance/
├── fp-and-a/            # Budgeting, forecasting, variance analysis
├── accounting/          # Bookkeeping, close process, reconciliation
├── tax/                 # Filing, planning, transfer pricing
├── treasury/            # Cash management, banking, FX, investments
├── investor-relations/  # Reporting, deck prep, cap table management
└── procurement/         # Vendor evaluation, contracts, spend management
```

Lifecycle: Plan → Record → Report → Tax → Invest → Procure

### C.4 Product Management

```
areas/product/
├── discovery/           # User research, problem framing, opportunity sizing
├── strategy/            # Roadmap, prioritization, OKRs
├── specification/       # PRDs, user stories, acceptance criteria
├── go-to-market/        # Launch planning, positioning, enablement
├── analytics/           # Product metrics, funnels, retention
└── growth/              # Activation, onboarding optimization, loops
```

Lifecycle: Discover → Prioritize → Spec → Build → Launch → Analyze → Grow

### C.5 Design

```
areas/design/
├── brand-design/        # Visual identity, logo, style guide
├── product-design/      # UI/UX, components, design systems
├── content-design/      # Copywriting within product (UX writing)
├── motion/              # Animation, video, interactive
├── research/            # User testing, usability, interviews
└── operations/          # Asset management, tooling, handoff
```

Lifecycle: Research → Brand → System → Product → Content → Motion → Handoff

---

## Appendix D — Agent-Specific Notes {#appendix-d}

This guide is designed to be agent-agnostic. However, different agents have different strengths and limitations to account for.

### D.1 Claude (Anthropic)

- Strong at following multi-phase procedures if each phase has a clear checkpoint.
- Best practice: start each session with `read GUIDE.md` before any generation.
- Load one phase at a time; don't ask Claude to complete all phases in one prompt.
- Claude handles long YAML frontmatter well — use full frontmatter in every artifact.
- For long builds: checkpoint after each spec (save outputs before continuing).

### D.2 Codex / GPT-4o / o-series (OpenAI)

- o-series models perform best when given explicit reasoning structure ("think step by step about the taxonomy before writing specs").
- GPT-4o handles parallel generation well — you can ask it to write all 3 rules for a spec simultaneously after the taxonomy is locked.
- Be explicit about bilingual requirement: state "write both EN and RU blocks" in every prompt — it doesn't persist from earlier instructions.
- Use system prompt to lock the area name and taxonomy; repeat it at the start of each session.

### D.3 Gemini (Google)

- Gemini 1.5+ handles very long context well — you can load the full GUIDE.md plus all previously written specs in one context window.
- Gemini tends to over-explain rules. Add instruction: "rules must be constraint statements only, no explanatory prose in the main body."
- For taxonomy design (Phase 2), Gemini benefits from explicit constraint: "output ONLY the spec list, do not generate content yet."
- Google Workspace integration: if building a marketing/legal/finance area, Gemini can directly reference real Docs/Sheets for domain analysis.

### D.4 Qwen 2.5+ / Qwen 3 (Alibaba)

- Excellent bilingual capability — EN/RU prompts can be written in either language; Qwen handles both natively.
- Strong on structured output. Use explicit output format instructions in each phase.
- For taxonomy: ask Qwen to output taxonomy as a markdown table with columns (spec name, owner role, primary tools, lifecycle stage) before creating directories.
- Qwen's code generation is strong — for technical domains, it will produce high-quality skill examples without additional prompting.

### D.5 GLM-5 / ChatGLM (Zhipu AI)

- GLM-5 responds well to clearly numbered instructions. Structure every phase prompt as a numbered list.
- Chinese-Russian bilingual capability is strong; if building for Chinese-market areas, consider adding ZH blocks alongside EN+RU.
- Frontmatter generation: GLM-5 sometimes omits YAML frontmatter — remind it explicitly: "include the full YAML frontmatter block before the markdown content."
- For rules: GLM-5 tends to write polite, hedged constraints. Add instruction: "use imperative voice; replace 'should' with 'must' everywhere."

### D.6 MiniMax 2.5 (MiniMax)

- Strong at creative/marketing domains — particularly well-suited for copywriting, brand, content areas.
- For structured artifacts: be explicit about file format ("output as a single markdown file with this exact structure: ...").
- MiniMax handles long-form generation well but may deviate from template structure. Provide the template inline in the prompt.
- Bilingual prompts: MiniMax handles EN/RU well; for RU blocks, prepend "Ответ на русском:" to ensure full Russian output.

### D.7 Llama 3.1+ / Open Source Models

- Context window varies significantly by deployment. For 8B/13B models: build one spec at a time, one artifact type at a time.
- For 70B+ models: similar capability to GPT-4o for structured generation tasks.
- Best practice: provide the template inline in every generation prompt (don't assume the model has the template in context).
- For taxonomy (Phase 2): smaller models benefit from few-shot examples. Show the devops or software taxonomy as a reference before asking for the new taxonomy.
- Quantized models (Q4/Q5): may struggle with YAML frontmatter; validate and fix frontmatter manually after generation.

### D.8 Universal best practices (all agents)

1. **One phase, one conversation turn.** Don't chain all 8 phases in one prompt.
2. **Always validate checkpoints.** Ask the agent "which checkpoint items are not yet complete?" before moving to the next phase.
3. **Save after each spec.** If context window resets, incomplete work is lost.
4. **Provide examples as anchors.** Before asking for a rule, show an existing rule as a reference. Same for skills, workflows, prompts.
5. **Lock the taxonomy early.** Once Phase 2 is complete, never change the spec names. Changing names mid-build causes orphaned files and broken references.
6. **Don't accept stubs.** If an agent produces a file < 50 lines for a skill or < 30 lines for a rule, reject it and ask for completion before continuing.
