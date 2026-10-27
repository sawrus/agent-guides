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

## Migrating to v3.0.0

1. Run `agentic upgrade` in each project. The gate hook commands now pass `--host claude|codex|opencode`.
2. Codex: open the project in Codex and trust the changed hooks in `/hooks`. Untrusted hooks do not run.
3. The gate guard now asks before production access (`kubectl`/`helm`/`oc` on a context that matches `prod`,
   database clients on `guard.prod_hosts`) and before database connections that read credentials from `.env`.
   It blocks write or maintenance SQL against a non-local database and any non-local database connection in host
   plan mode. On Codex an "ask" is a block with a request to run the command yourself.
4. To adjust, edit `.agent/gate.json`: `guard.prod_context_pattern`, `guard.prod_hosts`, `guard.confirm` (custom
   rules, added to the defaults), `guard.defaults: false` (turn the production defaults off), and `guard.db`
   (`{"mode": "ask|deny|off", "write": "deny|ask"}`).
5. Tools that read `.agentic/gate/last.json` get new fields (`accepted`, `reason_code`, `head`, `pack_version`,
   `profile`); the old fields stay.

## Migrating to v6.0.0

This release removes prompt files and two specializations, and makes workflows role-neutral. Run
`agentic upgrade` in each project, then check these points:

1. **`.agentic.json` is required.** `agentic upgrade` in a project with Agentic files but without
   `.agentic.json` now stops with an error. Earlier releases rebuilt such a project with
   `default + software.general` and removed the files of the real selection as obsolete. Run
   `agentic install --project-dir <dir> --agent-os <list> --areas <list> --specializations <list>` (or
   `agentic tui`) once with the settings you want. `agentic upgrade --force` keeps the old default rebuild.
2. **Prompt files.** `agentic` no longer installs `prompts/` (for example `.agent/prompts/*.md`). The upgrade
   removes unchanged prompt files. Prompt files you edited stay; delete them by hand when you no longer need
   them. Each workflow has an `Example request:` line instead.
3. **Removed specializations.** `software.full-stack` and `software.platform` no longer exist. The upgrade
   replaces them and prints a warning:
   - `software.full-stack` → `software.backend`, `software.frontend`, `software.general`
   - `software.platform` → `devops.kubernetes`, `devops.infrastructure`, `devops.ci-cd` (adds the `devops` area)

   `.agentic.json` keeps the new list. Rules, skills and workflows of the old specialization are removed when
   unchanged. Scripts that call `agentic install --specializations software.full-stack` keep working, but
   update them to the new ids. An unknown specialization now stops `install` and `upgrade` with the list of
   available ones (`agentic list specs --area <name>`).
4. **Role-neutral workflows.** Workflows no longer name roles or an initiator. With the `lean` profile the main
   session runs every step. With `team`, the Claude Code command wrapper and JEV ask the main session to send
   each step to the installed role agent that fits it (`developer` for code, `qa` for verification,
   `devops-engineer` for infrastructure), one subagent per step at most. Workflows that still name roles keep
   the old wrapper text.
5. **Removed and renamed workflows.** Ten workflows remain. Update scripts, docs, and habits that type a
   removed trigger:

   | Old trigger(s) | Use instead |
   |---|---|
   | `/development-cycle-workflow`, `/develop-epic`, `/create-endpoint`, `/test-feature`, `/project-setup-workflow`, `/develop-feature-fullstack`, `/feature-implementation-flow`, `/backend-project-full-cycle` | `/develop-feature` (now in `software.general`) |
   | `/debug-issue-fullstack`, `/debug-issue` (backend) | `/debug-issue` (now in `software.general`) |
   | `/refactor-module` (backend) | `/refactor-module` (now in `software.general`) |
   | `/alert-investigation`, `/db-incident`, `/service-incident`, `/postmortem` | `/incident-response` |
   | `/provision-environment`, `/destroy-environment`, `/drift-remediation`, `/module-development`, `/drift-check`, `/provision-env` | `/iac-change` |
   | `/pipeline-debug`, `/onboard-repo`, `/deploy-production` | `/release-pipeline` |
   | `/security-scan-pipeline`, `/security-scan` (software.security) | `/security-scan` (now in `devops.devsecops`) |
   | other spec workflows (frontend, mobile, mlops, data-engineering, qa, security, networking, observability, kubernetes onboarding and upgrades) | no replacement; the spec keeps its rules |

   A project that installs only `software.backend` gets `/add-migration`; add `software.general` for the
   general workflows.
6. **Removed and merged rules and skills.** Each topic now lives in one place. Renamed or merged rules:
   backend `architecture.md` → `service-architecture.md`; frontend `architecture.md` →
   `component-architecture.md`; ci-cd `quality-gates.md` and the general `gitlab-ci-guide.md` and
   `github-workflow-guide.md` → ci-cd `pipeline-standards.md`; sre `error-budget-policy.md` → `slo-policy.md`.
   Deleted: general `sdlc-role-responsibilities.md` and `sdlc-methodology-guide.md`. 84 of 98 skills are
   deleted; frontend, mobile, mlops, data-engineering, qa, and networking keep rules only. A company rule with
   `replaces: [...]` that names a removed pack rule must name its successor.
7. **Rules load by path.** Every rule now has `paths:` globs or `trigger: manual`. Claude Code loads a scoped
   rule only when you touch a matching file; manual rules stay in `.agent/rules/` and are read on demand.
8. **No Post-task review hook in pack workflows.** The role-neutral workflows have no `Post-task review`
   section, so `REVIEW_PIPELINE.md` runs only for a project workflow that adds the hook.

## Migrating to the lean-without-reviewer release

The `lean` profile no longer installs the `reviewer` helper subagent; it installs only `explorer`. The SDLC
benchmark (round 6, rule H4 in docs/agentic-v2-lean/README.md) never saw lean start the reviewer on the task built
to need it, and lean without it accepted the same cells. Run `agentic upgrade` in each project, then check these
points:

1. **Obsolete files.** The upgrade removes an unmodified `.claude/agents/reviewer.md`,
   `.codex/agents/reviewer.toml`, `.opencode/agents/reviewer.md`, and the `reviewer` entry in
   `.opencode/opencode.json`. A reviewer file you edited stays (`Preserved customized obsolete artifact`); remove
   it by hand if you no longer need it.
2. **Seeded profile.** An unedited `~/.config/agentic/<host>/profiles/lean/profile.json` from an older release
   (`"agents": ["explorer", "reviewer"]`, `"models": null`) follows the new built-in `lean` and is rewritten the
   next time `agentic profile` or the TUI runs. An edited `lean/profile.json` is used as written.
3. **Keep the reviewer.** Create a custom profile and add the helper, then switch to it:
   `agentic profile create lean-review --from lean`, add `"reviewer"` to `agents` in
   `~/.config/agentic/<host>/profiles/lean-review/profile.json`, and run `agentic profile use lean-review`.
   The `team` profile is unchanged.
4. **Core text.** `AGENTS.md` now asks for a reviewer subagent after a multi-module diff only when one is
   available (the host's native reviewer or an installed one).
