# Agentic Knowledge Maintenance

This guide defines how to update `areas/**` so copied agentic artifacts stay practical, current, and token-efficient.

## Weekly Upgrade Workflow

1. Pick one specialization at a time, for example `areas/software/full-stack`.
2. Read its `AGENTS.md`, all workflow front matter, prompt examples, and the current `docs/site/catalog.json` entry.
3. Identify one concrete industry change worth adding: a new delivery practice, framework release pattern, testing method, security control, observability practice, or operational runbook step.
4. Convert the change into the smallest useful artifact:
   - Rule: mandatory cross-cutting constraint agents must always follow.
   - Skill: task-specific procedure loaded only when needed.
   - Workflow: multi-role SDLC sequence with inputs, outputs, owners, gates, and failure path.
   - Prompt: examples that trigger an existing workflow with realistic project context.
5. Run the area quality audit and prompt/catalog checks through Makefile targets.
6. Document the behavior change under `docs/guidance-updates/` or a more specific `docs/<feature>/` path.

## What Qualifies As Useful Knowledge

- It changes an agent decision or action in a target project.
- It has a measurable quality gate, command, checklist, schema, or handoff.
- It is specific to a domain, stack, SDLC phase, or operational risk.
- It helps a developer get better implementation, review, verification, rollout, or incident response.

Avoid adding:

- Generic advice that a modern LLM already knows.
- Long explanations without a command, decision rule, or acceptance criterion.
- Duplicate guidance already present in a parent area.
- Tool-specific setup that should live in `extensions/**` or `docs/**` instead.

## Area Update Checklist

- `AGENTS.md` remains a navigation map, not a knowledge dump.
- Rules use imperative language and contain enforceable constraints.
- Skills explain when to load them and keep detailed references in separate files only when needed.
- Workflows define roles, `execution.initiator`, inputs, outputs, `uses-skills`, quality gates, and a failure loop.
- Prompts include two or three realistic EN/RU examples with concrete systems, symptoms, constraints, and expected deliverables.
- All `uses-skills` entries resolve to existing `skills/<name>/SKILL.md`.
- Token budget is improved or justified: remove stale skills before adding new ones.

## Practical SDLC Additions To Look For

- Requirements: acceptance criteria templates, non-goal capture, compatibility and migration constraints.
- Design: API contract review, data model risk, UX state inventory, security threat paths.
- Implementation: framework-specific safe defaults, dependency upgrade patterns, migration sequencing.
- Verification: contract tests, blackbox flows, accessibility checks, performance budgets, CI gates.
- Deployment: rollout strategy, rollback steps, feature flags, monitoring, release notes.
- Maintenance: runbooks, postmortem templates, cost/performance review, dependency freshness.

## Quality Bar

An update is ready only when it gives the target-project agent enough context to act without guessing:

- what to inspect;
- which role owns the step;
- what command or artifact to produce;
- what pass/fail condition applies;
- where the behavior is documented under `docs/`.

If an update cannot pass that bar, keep it out of `areas/**` until it becomes actionable.
