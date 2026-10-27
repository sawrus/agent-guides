---
name: {{kebab-case-skill-name — equals the directory name}}
description: {{WHAT_IT_DOES. Use when {{TRIGGER — the task or words that should load it}}. At most 1,024 chars.}}
related-rules:
  - {{rule-filename.md — only rules of the same spec}}
allowed-tools: {{COMMA_SEPARATED — only the tools the steps need, e.g. Read, Bash}}
---

<!--
AGENT INSTRUCTIONS (docs/artifact-standard.md, ART-C*, ART-S*):
1. A skill is an on-demand procedure the agent would not get right without it: numbered steps, decision
   points, exact commands, or a bundled script. It is not a topic overview or a tutorial.
2. `description` says when to load the skill ("Use when ..."), so the host can match it on its own. A workflow
   or rule of the same spec may also link it in `uses-skills`. A skill without either is an orphan.
3. Keep SKILL.md at most 250 lines; references and assets at most 400 lines in total. Code blocks are at most
   40 % of SKILL.md. Move long templates into a script or remove them.
4. No framework scaffolding (app generators, starter projects), no roles, no report files.
5. If the skill only restates a rule with code, keep the rule and delete the skill.
6. Run `make check-artifacts` and delete these AGENT INSTRUCTIONS before you finish.
-->

# {{DISPLAY_NAME}}

## Procedure

1. {{STEP — an exact command or check, e.g. "Run `kubectl get events -n <ns> --sort-by=.lastTimestamp`."}}
2. {{DECISION — "If {{condition}}, go to step 4; otherwise continue."}}
3. {{STEP}}
4. {{STEP — how to confirm the result, e.g. "Run `make test`; it must exit 0."}}

## Commands

```{{language}}
{{SHORT_COMMANDS_OR_SCRIPT_CALL}}
```
