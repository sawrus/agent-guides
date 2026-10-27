---
name: {{kebab-case-workflow-name}}
type: workflow
trigger: /{{kebab-case-workflow-name}}
description: {{ONE_SENTENCE, at most 200 chars — what completing this workflow produces}}
selection:
  general: {{false — true only for the one catch-all workflow of a top-level area}}
  use-when: "{{ONE_SENTENCE — the requests this workflow fits, judged by purpose, inputs and outputs}}"
  avoid-when: "{{OPTIONAL — a near-miss request that belongs to another workflow; delete the line if none}}"
uses-skills:
  - {{skill-directory-name — same spec only; use [] when none}}
related-rules:
  - {{rule-filename.md — same spec only; use [] when none}}
checks:
  - {{COMMAND that must pass, e.g. "make test"}}
artifacts:
  - {{OPTIONAL — paths the task must change or create, e.g. "docs/<feature>/README.md"}}
---

<!--
AGENT INSTRUCTIONS (docs/artifact-standard.md, ART-C*, ART-W*):
1. One workflow per kind of task in the whole pack. A variant for another stack is a step condition.
2. The main session runs the workflow. Do not add `roles`, `agent`, `execution.initiator`, `@role` handles,
   subagent instructions, or report files.
3. Write 3–6 steps. Each step has **Do** (actions) and **Done when** (a checkable condition).
4. The first step reproduces or states the current behaviour. A change workflow ends with the checks green
   and the docs updated per docs/regulation.md section 3 (covers: and Docs-Not-Needed).
5. A step that touches production (deploy, data change, cluster access) says "ask the user first".
6. "trigger" is `/` + `name` and is unique across all areas (see the area AGENTS.md trigger registry).
   "selection.use-when" is required, quoted, and at most 300 characters.
7. Keep the workflow at most 120 lines and 1,800 tokens.
8. Run `make check-artifacts` and delete these AGENT INSTRUCTIONS before you finish.
-->

# {{Workflow title}}

Example request: `/{{kebab-case-workflow-name}} "{{ONE REALISTIC REQUEST, no placeholders in the final file}}"`

## Steps

### 1. Reproduce

- **Do:** {{STATE OR REPRODUCE THE CURRENT BEHAVIOUR — e.g. "Run the failing test and record its output."}}
- **Done when:** {{CHECKABLE — e.g. "the failure reproduces with one command"}}

### 2. {{STEP_NAME}}

- **Do:** {{ACTIONS — exact commands, files, and decisions}}
- **Done when:** {{CHECKABLE CONDITION}}

### 3. {{STEP_NAME — e.g. "Deploy"}}

- **Do:** {{ACTIONS}}. Ask the user first before {{the production action, if any}}.
- **Done when:** {{CHECKABLE CONDITION}}

### 4. Verify and document

- **Do:** run the `checks` commands; update the docs page whose `covers:` matches the changed code, or add the
  commit trailer `Docs-Not-Needed: <reason>`.
- **Done when:** every `checks` command exits 0 and the docs coverage check passes.
