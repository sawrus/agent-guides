---
covers:
  - areas/**
  - areas/template/**
  - scripts/lint_prompts.py
  - scripts/check_artifacts.py
  - scripts/context_budget.py
  - scripts/check_artifacts.toml
  - scripts/check_artifacts_baseline.json
  - scripts/assess_area_quality.py
---

# Artifact standard: rules, skills, workflows

Status: draft for agreement (v1). It is the acceptance contract for every instruction artifact that agentic
ships from `areas/**` and for every company rule that a target project adds (`docs/company-rules.md`, planned).
`scripts/check_artifacts.py` (`make check-artifacts`) checks each requirement that has an `auto` mark and reports
its id. Reviewers check the `review` items by hand or with an LLM auditor ([regulation.md](regulation.md)).

## Why this exists

The agent already knows general engineering practice. An artifact earns its place only when it changes what the
agent does in a real project, and when someone can check that change. Every artifact costs context tokens, and
the measured benefit of the instruction layer is small (`docs/agentic-orchestration-research/README.md`,
findings 1–3). So the default answer to "should we add this?" is no.

## Principles

- **P1. Rules are the base.** A rule states a project constraint that a reviewer can check in a diff. Skills and
  workflows exist only to help the agent meet rules.
- **P2. One topic, one place.** Each topic lives in exactly one artifact. A rule beats a skill on the same topic.
  A company rule beats a pack rule on the same topic.
- **P3. Checkable, not textbook.** Write statements that a diff can pass or fail. Do not write tutorials, framework
  overviews, or code the model can produce on its own.
- **P4. No ceremony.** Artifacts do not assign roles and do not ask for report files. The output of work is code,
  tests, and the docs pages required by [regulation.md](regulation.md).
- **P5. Small and on demand.** Nothing is always-on unless it applies to every task in the project.

## Common requirements (all kinds)

| Id | Requirement | Check |
|---|---|---|
| ART-C1 | The file has YAML frontmatter with `description` (one sentence, ≤ 200 chars, says when the artifact applies). | auto |
| ART-C2 | No statement repeats the core `AGENTS.md` (definition of done, git branch and commit format, response style, process scaling). | auto (similarity) + review |
| ART-C3 | No near-duplicate of another artifact: shingle similarity below the threshold in `check_artifacts` config. | auto |
| ART-C4 | Every reference (`related-rules`, `uses-skills`, links to files) resolves inside the same install selection. | auto |
| ART-C5 | File names are unique across all specializations of an area that can be installed together. | auto |
| ART-C6 | No corporate data: hosts, URLs, group or service names, tokens. Use `gitlab.example.com`, `group/service`, `<url>`. | auto (deny list) + review |
| ART-C7 | No role assignments (`@pm`, `@team-lead`, "spawn one subagent per role") and no required report files (`*_report.md`, `*_summary.md`, `implementation_plan.md`). | auto |
| ART-C8 | English, plain style: short sentences, active voice, imperative mood. | review |
| ART-C9 | The artifact applies to the target segment: backend services, infrastructure, CI/CD, Kubernetes, observability, security of those. A stack-specific artifact names its stack in `paths` or `description`. | review |

## Rules

A rule is a set of constraints for one topic.

| Id | Requirement | Check |
|---|---|---|
| ART-R1 | Frontmatter has either `paths:` (globs where the rule applies) or `trigger: manual`. `trigger: always_on` is allowed only for rules that apply to every change in every project of the segment. Fields `glob`, `globs`, `model_decision` are not used. | auto |
| ART-R2 | ≥ 70 % of list items are checkable imperatives: they contain a verb such as *use, set, pin, add, keep, run, never, do not, must* and name a concrete object (file, flag, field, command, value). | auto (heuristic) + review |
| ART-R3 | ≤ 80 lines and ≤ 1,200 tokens. | auto |
| ART-R4 | Code blocks are short examples of the required form (≤ 15 lines each, ≤ 30 % of the file). | auto |
| ART-R5 | One topic. If a rule has more than one `#`/`##` heading for unrelated subjects, split it or cut it. | review |
| ART-R6 | Each statement is something a reviewer can verify in a diff, a config, or a command output. "Write clean code" fails. "Pin images by `@sha256` digest" passes. | review |

Example of a passing rule item: `Set resources.requests and resources.limits for every container.`
Example of a failing item: `Kubernetes is a container orchestration platform that ...`

## Skills

A skill is an on-demand procedure: steps, commands, or a script that the agent would not get right without it.

| Id | Requirement | Check |
|---|---|---|
| ART-S1 | `description` says when to load it (trigger words or situation), ≤ 1,024 chars. `name` equals the directory name (kebab-case). | auto |
| ART-S2 | The body is a procedure: numbered steps, decision points, exact commands, or a bundled script. Not a topic overview. | review |
| ART-S3 | ≤ 250 lines for `SKILL.md`; references and assets ≤ 400 lines in total. | auto |
| ART-S4 | Code blocks ≤ 40 % of `SKILL.md` lines. Long templates belong in a script or are removed. | auto |
| ART-S5 | No framework scaffolding templates (app generators, starter projects). | auto (deny list) + review |
| ART-S6 | At least one workflow or rule links the skill (`uses-skills` or a link), or the skill states a trigger that the host can match on its own. Orphans are removed. | auto |
| ART-S7 | The skill adds something beyond the rule on the same topic. If it only restates the rule with code, keep the rule and delete the skill. | review |

## Workflows

A workflow is an ordered checklist for one kind of task. The main session runs it. A host may delegate steps,
but the workflow does not ask for that.

| Id | Requirement | Check |
|---|---|---|
| ART-W1 | Frontmatter: `name`, `type: workflow`, `trigger: /<name>`, `description`, `selection.use-when`, `selection.avoid-when` (optional), `uses-skills`, `related-rules`, `checks` (commands that must pass, optional), `artifacts` (paths the task must change or create, optional). No `roles`, `agent`, `execution.initiator`. | auto |
| ART-W2 | 3–6 steps. Each step has **Do** (actions) and **Done when** (a checkable condition). | auto |
| ART-W3 | The first step reproduces or states the current behaviour; a change workflow ends with checks green and docs updated per [regulation.md](regulation.md) section 3. | review |
| ART-W4 | ≤ 120 lines and ≤ 1,800 tokens. | auto |
| ART-W5 | One workflow per kind of task in the whole pack. A variant for another stack is a step condition, not a new workflow. | review |
| ART-W6 | Steps that touch production (deploy, data change, cluster access) say "ask the user first". | auto (keyword) + review |

## Always-on budget

| Id | Requirement | Check |
|---|---|---|
| ART-B1 | For every installable specialization and for the common multi-spec selections, always-on text per host stays ≤ 4,000 tokens (`make context-budget`). | auto |
| ART-B2 | A new always-on artifact needs a measured reason (benchmark or field trace) in its PR. | review |

## Company rules

Company rules are rules that a target project or an organisation adds (`.agent/company/`, or an external
repository). They follow the same rule requirements (ART-C*, ART-R*). In addition:

| Id | Requirement | Check |
|---|---|---|
| ART-K1 | A company rule that covers the same topic as a pack rule replaces it: the rule names the pack rule in frontmatter `replaces: [<area>/<spec>/<rule>]`, and the project lists it in `company_rules.exclude`. | auto (`check_artifacts --project`) |
| ART-K2 | A company rule does not restate a pack rule that stays installed. | auto (similarity) |
| ART-K3 | Company rules may name internal systems; they never go into the public agent-guides repository. | review |

## Removal criteria

Remove an artifact from the pack when any of these is true:

1. It is textbook material (fails ART-R2/ART-R6 or ART-S2) and cannot be cut down to checkable statements.
2. It duplicates another artifact (ART-C3) — merge the useful lines into the surviving one first.
3. It targets a stack outside the segment (ART-C9) and no installed selection uses it.
4. It is an orphan skill (ART-S6).
5. It requires roles or report files (ART-C7) and the useful part already exists elsewhere.

## Automatic check

`make check-artifacts` runs `scripts/check_artifacts.py` (Python 3.11+, standard library only). It is part of
`make lint-content`, so CI runs it on every pull request.

- **Output.** One line per finding: id, file, short message. Each file gets a score: the share of applicable ids
  that pass. A summary counts files with findings per id. `--json` prints the same data for tools such as
  `agentic install`; `--verbose` also prints baselined findings and every file score.
- **Thresholds.** `scripts/check_artifacts.toml` holds every limit of this page, the ART-C2/ART-C3 similarity
  thresholds (word sets and 5-word shingles with Jaccard similarity), the ART-R2 verb and object lists, the
  ART-S5 scaffolding terms, and the ART-B1 common selections.
- **Ratchet.** `scripts/check_artifacts_baseline.json` lists the known findings as `<id> <path>` keys. The run
  fails only on a finding outside the baseline. A baseline key without a finding is reported as a stale baseline
  warning; `--strict-baseline` turns it into a failure. Regenerate the baseline with
  `make check-artifacts ARTIFACTS_ARGS=--write-baseline` only to shrink it.
- **ART-C1 for skills.** A skill description may be longer than one sentence; ART-S1 sets its limit
  (1,024 chars). The 200-char, one-sentence limit applies to rules and workflows.
- **ART-C5 scope.** Specializations of one area can be installed together, and their files land in the same
  target directories. The check reports equal `rules/<file>`, `skills/<dir>`, and `workflows/<file>` names
  across specs of one area.
- **ART-C6 deny list.** The repository holds only generic patterns: private keys, common token formats, and host
  addresses in private ranges. Company terms stay outside the repository: set `AGENTIC_DENY_TERMS_FILE` or pass
  `--deny-terms-file <path>`; the file has one term per line, `re:` for a regular expression, and `#` comments.
  The output names the line number of the term, not the term.
- **ART-S6 trigger.** A skill passes when a rule or workflow of the same spec lists it in `uses-skills` or names
  `skills/<name>`, or when its description states a trigger such as "Use when ...".
- **ART-W6.** Every step whose text mentions deploys, production, cluster changes, or data changes must also say
  "ask the user".
- **ART-B1.** The check installs every installable specialization alone and each common selection with the debug
  binary (`scripts/context_budget.py --all-selections`) and reports each selection over 4,000 tokens on any host.
  A specialization is installable when it has `rules/`, `skills/`, or `workflows/`; `prompts/` is not an install
  bucket.
- **No prompt files.** `agentic` does not install `prompts/`. A workflow carries its example as an
  `Example request: <text>` body line ([prompt-format.md](prompt-format.md)); `scripts/assess_area_quality.py`
  warns about a workflow without one.
- **Project mode.** `check_artifacts.py --project <dir>` checks the company rules in `<dir>/.agent/company/**`
  (ART-C1, C2, C3, C4, C7, R1–R4) against the pack rules installed in `<dir>/.agent/rules`. ART-K1 reports a
  company rule that covers the topic of an installed pack rule without `replaces:`, a `replaces:` entry that names
  no pack rule, and a replaced pack rule that is still installed. ART-K2 reports company statements that restate a
  pack rule. `--json` adds `replace_suggestions` with the `area/spec/rule` ids to put into `replaces:`.

## Change process

1. A PR that adds or changes an artifact runs `make check-artifacts` (part of `make lint-content` and CI).
2. A new artifact states in the PR which real task it changes and why an existing artifact cannot take it.
3. A removal lists the surviving artifact for each merged topic, so `tools/repo-scan/applicability.json`, JEV
   tests and benchmark tasks can be updated in the same PR.
