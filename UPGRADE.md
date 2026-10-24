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
- Workflows define roles, `execution.initiator`, a matching top-level `agent`, inputs, outputs, `uses-skills`, quality gates, and a failure loop.
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

## Migrating from the Bash CLI (v0.6.x) to the Rust binary (v0.7.0+)

1. Remove the old bash script if installed: `rm -f ~/.local/bin/agentic`.
2. Install the new binary: `curl -fsSL https://raw.githubusercontent.com/sawrus/agent-guides/main/install | bash`.
3. The local knowledge-base checkout at `~/.local/share/agentic/repo` is no longer used (content is embedded in the binary); you may delete it.
4. Existing projects with `.agentic.json` keep working: run `agentic install --project-dir <dir>` or `agentic upgrade` inside the project to re-sync.
5. `npx @jetrabbits/agentic@latest` keeps working from v0.7.0: the npm package is now a thin launcher that downloads the release binary on first run.
6. `fzf` is no longer needed — the TUI is built in.

## Migrating to v2.0.0

v2.0.0 changes the default install. Run `agentic upgrade` in each project, then check these points:

1. **Profile.** Projects without a saved profile move to `lean`: the nine role agents and the
   `product-owner` main-session setting are no longer installed. To keep the v1 team, run
   `agentic install --project-dir <dir> --profile team` once; the choice is saved in `.agentic.json`.
   Projects with JEV enabled and a saved `team` profile, or with JEV and no saved profile, stay on `team`.
   JEV no longer selects `team` by itself: a new `--enable-jev` install without `--profile` is `lean`
   (see "Lean + JEV" in docs/jev-integration/README.md). Pass `--profile team` to keep the role team.
2. **Obsolete files.** The upgrade removes unmodified role agents and manual rules that the new profile no
   longer installs (for example `.claude/agents/product-owner.md`, `.claude/rules/architecture.md`). Files you
   edited stay; remove them by hand if you no longer need them. Manual rules remain in `.agent/rules/`.
3. **Quality gate.** The Stop and PreToolUse hooks are on by default. Codex shows them in `/hooks`; trust
   them there. Configure the check commands in `.agent/gate.json` when the project has no `make test` or
   `make lint`. Use `--disable-gate` to opt out.
4. **Codex skills.** Skills now also install to `.agents/skills/`.
5. **Verify.** `make context-budget` in this repository shows the always-on estimate per host. In the
   project, `.agentic/gate/last.json` shows the last gate run.
