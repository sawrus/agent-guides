---
description: {{ONE_SENTENCE, at most 200 chars — when the rule applies, e.g. "Constraints for Kubernetes Deployment manifests."}}
paths:
  - "{{GLOB — files where the rule applies, e.g. k8s/**/*.yaml}}"
---

<!--
AGENT INSTRUCTIONS (docs/artifact-standard.md, ART-C*, ART-R*):
1. Scope the rule with `paths:` globs. Use `trigger: manual` instead of `paths:` only when no file pattern fits.
   `trigger: always_on` is only for a rule that applies to every change in every project of the segment.
   Do not use `glob`, `globs`, or `model_decision`.
2. One topic per rule. Write each item as a checkable imperative with a concrete object (file, flag, field,
   command, value): "Pin images by `@sha256` digest." At least 70 % of list items must pass this test.
3. Do not explain the technology, assign roles, or ask for report files. Do not repeat the root AGENTS.md
   (definition of done, git format, response style).
4. Keep the rule at most 80 lines and 1,200 tokens. A code block is a short example of the required form
   (at most 15 lines; code is at most 30 % of the file).
5. Run `make check-artifacts` and delete these AGENT INSTRUCTIONS before you finish.
-->

# {{TOPIC — noun phrase, e.g. "Kubernetes workload manifests"}}

- {{IMPERATIVE — e.g. "Set `resources.requests` and `resources.limits` for every container."}}
- {{IMPERATIVE — e.g. "Pin every image by `@sha256` digest; never use `:latest`."}}
- {{IMPERATIVE — e.g. "Add `readinessProbe` and `livenessProbe` to every long-running container."}}

Example of the required form:

```{{language}}
{{AT_MOST_15_LINES — the shape that passes the rule}}
```
