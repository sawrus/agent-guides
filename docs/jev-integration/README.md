---
covers:
  - extensions/codex/hooks/jev/**
  - extensions/opencode/hooks/agentic-jev.ts
  - src/jev_hooks.rs
  - src/jev_defaults.rs
  - src/hookmerge.rs
  - scripts/blackbox_jev.py
  - scripts/blackbox_calculator_probe.*
  - scripts/pilot_jev.py
  - scripts/check_jev_sdk.py
---

# JEV native hooks

See [native verification results](verification.md) for measured outcomes and limits.

## Behavior and acceptance criteria

Agentic 1.3.0 replaces JEV skill calls and workflow-specific Markdown checkpoints
with native hooks for **Codex 0.161.0+** and **OpenCode V2 2.0.28+**. Agentic 1.4.0
adds **Claude Code** (hooks in `.claude/settings.json`; see
[Claude Code adapter](#claude-code-adapter)). Rust handles activation and
installation; `.agent/jev/hook.py` handles typed decisions and
`.opencode/plugins/agentic-jev/index.ts` adapts the OpenCode V2 API. Python 3.10+
is required at runtime. The Gemini adapter, semantic test-evidence evaluation,
fix-loop control and epic prioritization are deferred. No extra workflow runner
or JEV MCP server is installed.

Adapter sources belong to `extensions/codex/hooks/jev/` and
`extensions/opencode/hooks/agentic-jev.ts`. The common Python runtime is deployed
to `.agent/jev/`; the OpenCode adapter is deployed to its native plugin directory.
The runtime has six stdlib modules (prepared.py is loaded for Codex preselection):

| File | Purpose |
| --- | --- |
| `hook.py` | Entry point, event pipeline, permission boundaries, audit records, review packet |
| `questions.py` | Workflow catalog, repository snapshot, request builders, permission metadata, thresholds |
| `routing.py` | Model pools, tiers, prices, role defaults, deterministic spawn rules |
| `adapters.py` | Codex and Claude Code payload translation and hook output |
| `api.py` | JEV client: validation, credentials, redaction, evaluation |
| `prepared.py` | Explicit Codex preselection, expiring single-use records and native correlation |

`hook.py` asks JEV only when `api.py`, `questions.py`, `routing.py` and
`adapters.py` are present with runtime version 2. Otherwise every event returns
`fallback/runtime_incomplete` (Codex and Claude get an empty hook output) and the
host keeps its native behavior. When JEV is enabled, the hook still writes one
record per event with identifiers only (host, kind, session, event and tool ids),
never the prompt or tool input.

On the original user prompt, JEV chooses from the workflows actually installed
in `.agent/workflows/`. The host receives context directing it to load and execute
the selected workflow with its native roles. Explicit workflow requests remain
unchanged. This is a context instruction; actual execution must be verified from
native tool evidence, not merely from JEV's recommendation. The exact questions
are in [Questions, tiers and records](#questions-tiers-and-records).

Before creating a subagent, JEV chooses the least expensive sufficient model
**tier** for the role's assignment. The hook maps the tier to a concrete model.
Candidates are restricted to the models assigned by the installed project's role
profiles and tiers, intersected with the host's available catalog and known
availability restrictions. Role title alone must not inflate complexity. Codex
uses its native model cache; OpenCode uses its runtime catalog, capabilities and
prices. Codex `PreToolUse` rewrites the native spawn
arguments; OpenCode rewrites `subagent.model`. Native role permissions remain.
Explicit tool model assignments, models written in local role Markdown, manual
local configuration changes and continuing existing children are preserved.
Inherited role models and unchanged Agentic mapper assignments are defaults that
JEV can route. Mapper state records `model_defaults`; changing a local role model
relative to that snapshot makes it a pin. Selected bundled/custom OpenCode profile
defaults are recorded in `.agent/jev/opencode-profile-defaults.json`; unchanged
profile assignments are also routable. OpenCode installs also get
`.agent/jev/opencode-model-tiers.json`, the shipped tier map; its models join the
candidate pool (see [Model question](#model-question)). Legacy mapper states without a snapshot
conservatively retain local model pins. To reconfigure them, back up and move
`.opencode/agent-model-mapper.state.json` out of that path, then select the mapper
in Agentic TUI and confirm the desired defaults again. Root `opencode.json` role
models also remain explicit pins. If a local configuration cannot be safely parsed
(including JSONC comments), model routing falls back without a paid request.
Production considers all active providers, not just OpenAI. Catalog visibility
means quota is unknown unless verified. Observed OpenCode HTTP auth/quota failures
exclude that model from subsequent decisions for 15 minutes (429: one minute);
no paid availability probes or unproven quota claims are made.
Bundled Codex role defaults and tiers are recorded in `.agent/jev/model-defaults.json`
and omitted from native TOML when enabled so they do not override hook decisions;
explicit models in user profiles also enter the pool and remain pinned for that role. User-edited profiles are
protected. Missing/unknown prices do not prove cheapest. Reviewer selection uses
comparable input+output catalog prices, otherwise `AGENTIC_JEV_REVIEW_MODEL` or
`settings.jev.lightweight_model`; the Codex default is available `gpt-6-luna`.

Permission evaluation can return allow/deny/ask. JEV receives metadata only: no
file content and no full command text. Requests that cannot be auto-allowed are not sent
to JEV; the host decides natively. Explicit native denials remain
final. Automatic approval is bounded to project/system temporary paths with
sandbox preserved. Secrets, deletion, outside paths, network/escalation and
symlink escapes require native approval. Shell operands resolve from the actual command cwd;
missing, relative or unresolvable cwd retains native approval. Arbitrary shell commands are assessed,
but only simple provably bounded commands may be auto-approved; interpreters,
substitutions, pipes and redirects remain native approval requests. Codex Bash
PermissionRequest represents escalation/network approval and is never auto-allowed.
JEV does not execute commands or grant sandbox exemptions.

Errors, unavailable keys/catalogs, timeout (eight seconds), oversized requests,
confidence below the question's threshold (model 0.6, workflow and permission 0.9) and duplicate in-flight
events retain native behavior; a spawn fallback applies the role default instead
(see [Model question](#model-question)).
The same native event is evaluated once; no retry requests for a preferred answer.
Disabled integration makes no requests and does not read credentials.

Some Codex transports expose encrypted subagent assignments to hooks. The audit
marks `assignment_unavailable`; JEV receives original scope and role metadata,
not decrypted content. Confidence assesses capability fit, while price and quota
can remain unknown. Ambiguous capability requirements still trigger fallback.

## Questions, tiers and records

JEV receives one question per event. All state is untrusted evidence. Requests
are serialized as UTF-8 (`ensure_ascii=False`) and must stay under 32 KiB; a
catalog of 80 workflows with a Cyrillic prompt fits.

### Workflow question

Sent on the original user prompt when no explicit `/trigger` or workflow id
matches.

- **Options:** every `.agent/workflows/*.md` with `type: workflow`, plus `native`
  and `clarify`. Each option text holds the description, `inputs → outputs`,
  roles and `selection.use-when` (and `avoid-when` when present). The workflow
  with `selection.general: true` starts with `GENERAL.`. A large catalog drops
  roles, then inputs/outputs, then shortens `use-when` to fit a 20 000-byte
  option budget.
- **State:** `original_request` (≤ 3000 characters, with
  `original_request_truncated`), `installed_areas` (from `.agentic.json`) and
  `repository`: `is_git`, `source_files`, `top_languages`, `has_makefile`,
  `has_ci`, `only_agent_guidance`, `truncated`. The snapshot walks at most 5000
  entries, depth 6, for 0.3 s; it does not follow symlinks or enter hidden,
  `node_modules`, `target`, `vendor`, `dist` and `build` directories. The workflow
  catalog itself is not repeated in state.
- **Instruction (summary):** choose the workflow whose purpose, inputs and outputs
  fit the original request; `GENERAL` covers ordinary requests; missing details do
  not make the choice uncertain; an empty repository does not turn a build request
  into a setup request; `native` for answers, explanations and analysis; `clarify`
  when a change is asked but its goal or target is unknown.
- **Result:** a confident workflow id adds `result.workflow` with `id`, `path`,
  `description`, `trigger`, `initiator` and `roles` (empty for role-neutral
  workflows without `roles` and `execution.initiator`). `native` gives
  `fallback/native_request`, `clarify` gives `fallback/clarification_needed`; both
  keep native host behavior.

### Model question

Sent before a subagent spawn, after these rules (no JEV call):

1. `project_configuration_unavailable`, an explicit model or a role-file pin, or
   a continued child keeps native behavior (`model_source: pinned`).
2. Under `lean`, the helpers `explorer` and `reviewer` never get a tier above the session model's tier. When
   that tier is unknown, the cap is `balanced`. Models above the cap leave the candidates and the role default.
   When no candidate is left, the result is `fallback/tier_above_session` with no model, and the host runs the
   helper on the session model. The session model comes from the Codex payload `model`, the last assistant
   model in the Claude transcript, or the OpenCode root session's last primary request.
3. A single eligible model is routed (`single_eligible`).
4. `instruction-reviewer` gets the cheapest priced or configured lightweight
   model. When neither exists, it gets the `fast` tier model with reason
   `tier_fast_price_unknown`. All three use `model_source: review_model`.
5. Fewer than two resolved tiers give `fallback/no_tier_routing`.
6. A Codex spawn (only Codex) with an encrypted assignment (`assignment_unavailable: true`)
   without prepared metadata gives `fallback/assignment_unavailable`, and the role default applies.
   Use the [explicit preselection interface](#codex-preselection) before encryption when the exact assignment is available.

- **Options:** the available tiers `fast`, `balanced`, `frontier`, plus `clarify`.
  The rubric: `fast` for bounded work with an established pattern; `balanced` for
  ordinary multi-file work that needs engineering judgment; `frontier` only when
  the assignment itself needs novel architecture, security, concurrency or
  migration decisions; `clarify` when the sufficient capability is unknown.
- **State:** `original_request`, `role`, `role_description`, `role_default
  {model, tier}`, `assignment` (≤ 2500 characters, with `assignment_truncated`),
  `assignment_unavailable`, `workflow {id, roles}`, `candidates [{tier, model,
  relative_cost}]`, `cost_source` and `quota: "unknown"`. The session model is not
  sent.
- **Tier mapping per host:**

  | Host | Capability source | Cost evidence |
  | --- | --- | --- |
  | Claude | profile tiers or explicit alias map | unknown without catalog prices |
  | Codex | installed model-defaults tiers and candidate overrides | unknown without catalog prices |
  | OpenCode | installed opencode-model-tiers.json and candidate overrides | selected catalog prices only |

  Price never creates a capability tier. OpenCode uses the explicit map even when
  stronger models are cheaper, prices are equal, or providers differ. A provider
  needs at least two available mapped models. Preference remains
  AGENTIC_JEV_MODEL_PROVIDER, then the role default's provider, otherwise the
  first qualifying provider in map order. Settings overrides win only for available candidates.
  Missing/malformed maps and unknown priced models do not invent capabilities:
  fewer than two resolved tiers gives fallback/no_tier_routing and the role default.
  The plugin still filters model availability, tool support and provider restrictions.

  relative_cost is a ratio only when every selected price is finite and positive;
  otherwise it is null, never 1/2/3 inferred from capability order. cost_source
  retains catalog_price, tier_map and tier_order compatibility labels; the last
  two describe map/configuration provenance and do not prove price ordering.
- **Fallback:** `clarify`, low confidence, an API error or `no_tier_routing`
  apply the role default when it is a candidate, on every host:
  `status: fallback`, `model_source: role_default`. Codex and Claude read it from
  `model-defaults.json` (`role_default_source: defaults`). On OpenCode the hook
  resolves it:
  - The plugin sends `role_default` (the agent's model, else the selected
    profile default). If that model is in the catalog, it wins
    (`role_default_source: profile`).
  - Otherwise the role's tier from the map `roles` applies
    (`role_default_source: role_tier`). `balanced`: product-owner, team-lead,
    developer, devops-engineer and native `general`. `fast`: qa, analyst, pm,
    instruction-reviewer, memory-curator and native `explore`. These mirror the
    Codex role defaults; a content test checks the parity. `frontier` is never a
    role default.
  - A role with no tier keeps the native model (`model_source: none`).

  So a default OpenCode install (`opencode-profile-defaults.json` is `{}`) still
  resolves a role default for every installed role. Pinned spawns and
  `project_configuration_unavailable` never get a role default. The Codex `qa`
  default is `gpt-6-luna` (`fast`), so it is a tier candidate.

### Permission question

- **When it is asked:** only when `permission_boundaries` marks the request
  `auto_allow_eligible`. An ineligible request is never sent to JEV: JEV could not
  allow it, and metadata alone cannot prove hostility. The record shows
  `status: fallback`, `reason_code: not_auto_allow_eligible`, `outcome: native`,
  `applied: false`, `decision: null`, and the host asks the user natively
  (Codex and Claude get an empty hook output; OpenCode gets no decision).
- **Options:** `allow`, `deny`, `ask`.
- **State:** `original_request`, `action`, `targets [{path, in_project, new_file,
  bytes, kind}]`, `command {program, length,
  args, shell_operators}`, `agent` (an installed role or `null`),
  `native_agent_type`, `workflow {id, roles}`, `approved_decisions` (the last 10
  applied `{action, targets, decision}` of the task) and `auto_allow_eligible`.
- **Targets:** the hook inspects only paths that resolve inside the project or the
  system temporary directory (`$TMPDIR/…`) and do not look sensitive. For those,
  `bytes` is the current size on disk (0 for a new file) and `kind` is `source`,
  `test`, `docs`, `config`, `directory` or `other`. A path that resolves outside
  both roots, including through a symlink, is shown as `[outside project]` with
  `kind: outside`; a sensitive path (`.env`, keys, credentials) gets
  `kind: secret_like`. Neither is stat-ed: `bytes` and `new_file` are `null`, and
  the raw outside path is never sent.
- **Instruction additions:** earlier approved decisions show task context but do
  not authorize this request; if `auto_allow_eligible` is false, do not choose
  `allow`. The `allow` → `ask` downgrade (`outcome: ask_downgrade`) stays as a
  safeguard. `permission_boundaries` decides eligibility and is unchanged.

### `model-defaults.json` v2

```json
{"version": 2,
 "roles": {"developer": "sonnet", "team-lead": "opus"},
 "tiers": {"fast": "haiku", "balanced": "sonnet", "frontier": "opus"}}
```

Claude-only installs record the Claude profile aliases; any install with Codex
records Codex ids and `model-tiers.json`. Since 1.5.0 an install with Codex and
Claude also writes `hosts.claude` (`{roles, tiers}` from the Claude profile), and
Claude spawns read that section. Before, the Codex ids gave Claude no alias, so a
low-confidence Claude spawn inherited the coordinator's model (for example opus). The hook still reads the legacy flat
`{role: model}` file: roles work, tiers are empty, so the model question is not
asked and the role default applies.

### Thresholds

`settings.jev.thresholds.{workflow, model, permission}` in `.agentic.json` set the
minimum confidence per question. A value is used only when it is a number in
[0.5, 1]; anything else gives the default: 0.6 for `model`, 0.9 for `workflow`
and `permission`. A wrong tier costs one subagent run, and below the threshold the
role default from the installed profile applies, never the parent session model. Reinstall keeps `thresholds`,
`lightweight_model` and `tiers`.

```json
{"settings": {"jev": {"enabled": true, "thresholds": {"workflow": 0.9, "model": 0.8, "permission": 0.95}}}}
```

The permission floor of 0.5 is safe only because `auto_allow_eligible` still
applies: rejected requests are not sent to JEV at all, so a low threshold can
never auto-allow or auto-deny a request that `permission_boundaries` rejects.

### Reason codes

| Code | Meaning |
| --- | --- |
| `explicit_workflow` | A `/trigger` or workflow id in the prompt; JEV not asked |
| `session_follow_up` | A later user prompt in a session that already has a task; JEV not asked |
| `session_off` | JEV is off for this session (first prompt chose no workflow, or `/jev off`); JEV not asked, spawns get the role default |
| `native_request` | JEV chose `native` |
| `clarification_needed` | JEV chose `clarify` (workflow or model) |
| `low_confidence` | Confidence below the question's threshold |
| `no_tier_routing` | Fewer than two tiers resolved; role default applies |
| `assignment_unavailable` | Codex spawn with an encrypted assignment; JEV not asked, role default applies |
| `tier_fast_price_unknown` | `instruction-reviewer` routed to the `fast` tier: no prices and no lightweight model |
| `not_auto_allow_eligible` | Permission request outside the automatic boundary; JEV not asked, host decides |
| `runtime_incomplete` | `api.py`, `questions.py`, `routing.py` or `adapters.py` missing or of another version; one identifier-only record is written |
| `explicit_model_or_continuation` | Pinned model or continued child |
| `single_eligible_model` | One candidate |
| `tier_above_session` | Lean `explorer` or `reviewer`: every candidate is above the session tier (`balanced` when unknown); the helper runs on the session model |
| `request_failed`, `missing_key`, `invalid_endpoint`, `request_too_large` | Client or API failure |

`no_matching_workflow` is no longer produced.

### Decision record fields

Every `event-*.json` for a prompt, spawn or permission event has these top-level
fields next to `context`, `request` and `result`:

| Field | Values |
| --- | --- |
| `decision` | Raw JEV choice, or `null` when JEV was not asked or failed |
| `threshold` | Threshold used for this question type |
| `applied` | `true` when the confident JEV choice decided the outcome (including `native` and permission `ask`) |
| `outcome` | `jev_applied`, `role_default_applied`, `rule_applied`, `ask_downgrade` or `native` |
| `tier` | Spawns: tier of the applied model, or `null` |
| `model_source` | Spawns: `jev_tier`, `role_default`, `single_eligible`, `review_model`, `pinned` or `none` |
| `cost_source` | Spawns: `catalog_price`, `tier_map`, `tier_order` or `null` (no tiers) |
| `role_default_source` | Spawns: `profile`, `role_tier`, `defaults`, or `null` (none resolved, or a deterministic rule decided) |

Spawn results also carry `tier` and `model_source`. `result.status`,
`result.model` (always a concrete model, never a tier) and `context` keep their
meaning for `scripts/blackbox_jev.py`. Observations of subagent types that are
not installed roles have `agent: null`. Claude `SubagentStart` has no model; the
observed model comes from the transcript at `SubagentStop`.

## Lean + JEV

JEV works with both install profiles. The hooks read `settings.profile` from `.agentic.json`. A manifest
without a profile counts as `team`, because JEV installed the role team before profiles existed.

| | `lean` + JEV | `team` + JEV |
|---|---|---|
| Agents | `explorer`, `reviewer`, native main session | nine SDLC roles, `product-owner` main session |
| First prompt | one workflow call per session | one workflow call per session |
| `native`, `clarify`, low confidence | no context; the session turns JEV off | no context; the session turns JEV off |
| Workflow chosen | one sentence: use the workflow file as a checklist and perform its steps yourself; start a subagent only where the core rules ask | load the workflow, act as its initiator, delegate to its role agents; a role-neutral workflow runs in the main session and sends each step to the installed role agent that fits it, one subagent per step at most; Codex prepared spawns; post-task review packet |
| OpenCode | no switch to the workflow initiator | switch to the initiator when it is installed |
| Plan mode | one sentence: perform only the diagnosis and analysis steps, present the rest as a plan, do not edit files | same as `lean` |
| Spawn routing | models of `explorer`, `reviewer` (never above the session tier), and native agents | models of the role agents |
| Codex | thread default; helpers keep `model_reasoning_effort` | `agents.max_threads = 8`; role profiles lose `model` and `model_reasoning_effort` |
| Quality gate | unchanged | unchanged |

Install: `agentic install --enable-jev` (lean is the default) or `agentic install --profile team --enable-jev`.
A project that saved `team` stays on `team` after `agentic upgrade`. Benchmark arms `lean-jev` and `team-jev`
compare both (docs/agentic-v2-lean/README.md, "Benchmark").

Measured in round 4 (docs/agentic-v2-lean/results.md, 21 cells per host and arm): lean + JEV accepted as many
tasks as lean on Claude and Codex (21/21) and 2 fewer on OpenCode (17/21). Cost per accepted task was 1.02 ×
lean on Claude, 1.12 × on OpenCode, and 1.43 × on Codex, where routing sent helper spawns to a frontier model.
JEV picked a workflow in 3 of 21 sessions and answered `native` in the rest. Lean + JEV stays opt-in.

Plan mode is read-only. Claude Code sends `permission_mode: plan`; in OpenCode the session agent is `plan`. Then
the workflow hint asks the session to do only the workflow's diagnosis and analysis steps (read, search, reproduce
without changes) and to present the remaining steps as a plan. Codex payloads have no plan mode, so the hint does
not change there. The text lives in `adapters.py`; the OpenCode plugin sends `plan_mode` and appends the
`context` that the hook returns.

OpenCode code mode reports one MCP call twice under one call id: as the `execute` wrapper and as
`<server>_<tool>`. The plugin and the hook keep one tool record per call id, with the concrete tool name.

## Claude Code adapter

`agentic install --agent-os claude --enable-jev` merges six owned hook groups into
`.claude/settings.json`. Each runs
`python3 "$CLAUDE_PROJECT_DIR/.agent/jev/hook.py" --host claude`. Ownership is
recorded in `.agentic/claude-jev-hook-entries.json`. User hooks and other settings
keys stay unchanged. Disable removes only unmodified owned groups.

| Claude event | JEV decision | Native application |
| --- | --- | --- |
| `UserPromptSubmit` | Workflow from `.agent/workflows/` | `additionalContext`: load the workflow, act as its initiator, delegate through the Agent tool |
| `PreToolUse` (`Agent\|Task`) | Model for the role in `subagent_type` | `updatedInput.model` with `permissionDecision: allow` |
| `PermissionRequest` | allow / deny / ask | `decision.behavior`; `ask` keeps the native prompt |
| `PostToolUse` | Observation | Records reads of `.agent/workflows/*.md` and `.claude/commands/*.md` |
| `SubagentStart` | Observation (Claude sends no model here) | Review packet path for `instruction-reviewer` |
| `SubagentStop` | Observation | Observed model from `agent_transcript_path` |

The Agent tool accepts only the aliases `opus`, `sonnet` and `haiku`.
Candidates are those aliases, restricted to the aliases that the selected Claude
profile assigns (`.agent/jev/model-defaults.json`). Tiers map to aliases:
`fast` → `haiku`, `balanced` → `sonnet`, `frontier` → `opus` (profile `tiers`).
If the recorded tiers are not aliases (a combined Claude + Codex install records
Codex ids), the hook uses this built-in alias map. A result that is not an alias
is never applied. `haiku` is the lightweight reviewer model. When JEV is enabled,
`model:` is left out of `.claude/agents/*.md` so the hooks can route each spawn.
An explicit `model` in the Agent call, or a `model:` that a user adds to a role
file, is a pin and is preserved. Claude does not need a hook trust review.

Claude-specific rules:

- Claude Code delivers subagent hand-backs (`<agent-message …>`) and background
  task notifications (`<task-notification>`) through `UserPromptSubmit`. The hook
  ignores them: they continue the current task, so the original request stays the
  context for the next spawn decisions, and no extra workflow selection runs.
- `AskUserQuestion` and `ExitPlanMode` are dialogs with the user, not permission
  boundaries. The hook never sends them to JEV.
- The session model is not part of the model question. JEV judges the
  assignment against the tiers only.
- When JEV gives no confident answer (`low_confidence`, `clarification_needed`,
  request failure), the hook applies the role's alias from the selected Claude
  profile (`.agent/jev/model-defaults.json`, for example `developer` → `sonnet`).
  The record keeps `status: fallback` and adds `model_source: role_default`; the
  hook reason reads `Role default sonnet`. Blackbox counts only `evaluated`
  answers as JEV routing. A role without a profile alias (for example `Explore`),
  an explicit `model` and a role-file pin are left unchanged, so only those spawns
  inherit the session model.
- `PermissionRequest` sends `agent_type` as `agent` only when it names an
  installed role in `.claude/agents/`; otherwise `agent` is `null` and the raw
  value is kept as `native_agent_type`. Observations follow the same rule.

## Session gate and manual switch

Since 1.5.0 JEV decides once per session, at the first root prompt
([requirements](session-gate/README.md)):

- **First prompt.** One workflow question. A selected workflow keeps JEV on for
  the session. `native`, low confidence or an error turns JEV **off** for the
  rest of the session (`off_reason` in the context file). `clarify` leaves the
  session undecided, so the next prompt is asked again.
- **Later prompts.** No workflow question and no new task: answers, approvals and
  "how did JEV do" questions stay bound to the first task. A prompt that names a
  workflow (`/develop-feature`, or its id) starts a new task without a call.
- **Off session.** Prompts and permissions make no calls (`session_off`). Spawns
  make no calls either but still get the role default, so they never inherit the
  coordinator's model.
- **Manual switch.** `/jev off`, `/jev on` and `/jev status` work in every host.
  Claude Code and OpenCode get a `jev.md` command; in Codex type `jev off`
  (without the slash) if the TUI rejects the unknown command. Claude Code and
  Codex hooks block the prompt, so the switch costs no model turn; OpenCode
  replaces it with a one-line confirmation. `/jev on` is the explicit new-task boundary.
  It forgets the task and approval history; the next prompt asks for a workflow again.
  Task generations isolate cached permissions, prepared spawns and review packets.
  Automatic goal-change detection is a separate, unimplemented capability. Task generations isolate cached permissions and prepared spawns; old approval history is cleared.

The switch is per session. The project switch (`settings.jev.enabled`) and
`AGENTIC_ENABLE_JEV=0` still turn JEV off for every session.

## Enable and disable

```sh
make build
./target/debug/agentic tui --no-doctor
```

Select the target project, Codex/OpenCode/Claude, areas and JEV beside Context7.
Activation and masked key entry stay in the existing TUI. There is no server
picker. Key entry preserves unrelated `.env` assignments, ignores `.env`, and
restricts Unix permissions to 0600. Installation itself makes no paid requests.

```sh
./target/debug/agentic install --project-dir /path/to/project \
  --agent-os codex,opencode,claude --areas software \
  --specializations software.backend,software.general --enable-jev --no-doctor
```

The default server is **TypeSafe AI (official API)**:
`https://api.typesafe.ai/v1/systemone`, with `TYPESAFE_API_KEY` from environment or
project `.env`. Buy official quota at [TypeSafe console](https://console.typesafe.ai/keys).
For the purchased test gateway, use `JEV_API_KEY` and:

```sh
JEV_API_URL=https://jevtypesafeai.com/api/v1/decide ./target/debug/agentic tui --no-doctor
```

`--jev-api-url` also overrides the URL. Installer precedence is CLI > OS variable
> saved manifest > official default. Runtime OS override wins over the saved URL.
No redirect following, key/provider fallback or secret execution from `.env` occurs.

Uncheck JEV in TUI or use `--disable-jev`. The saved false flag wins over enable
arguments/replay. Unmodified managed adapters and individual owned Codex hook
entries are removed; edited/unmanaged assets and foreign hooks are preserved with
warnings. Conflicting entries require manual reconciliation. Old skill files are
removed only with matching recorded ownership/hash; edits remain local.

Codex requires **native trust review** of project hooks through `/hooks` before
calls run. Agentic never trusts definitions automatically or adds trust bypass
flags. Changed definitions require review again. Codex CLI 0.153 removed
`--no-daemon`; pass the project with `-C` instead. OpenCode discovers
its local plugin automatically; legacy V1 plugins/auth integrations may need their
own V2 migration independently of JEV.

Install and upgrade ignore directories `.agentic*/` and `.review*/`; they do not
ignore the tracked `.agentic.json` file. Upgrade staging includes `.gitignore` and
hook-entry ownership metadata, while keeping Q/A logs out of synchronization.

## Audit and post-task review

Cleansed full questions, responses, context, usage and native observations live
in `.agentic/jev/event-*.json`, with 30-day retention and event deduplication.
They contain session/task/tool identifiers; exact local JEV keys and secret
assignments are removed before sending and writing. Native observed model may be
unknown: a requested model alone does not prove application.

The existing REVIEW_PIPELINE runs its specialist pair once after successful
top-level delivery. Supply only that task's audit records. Instruction reviewer
assesses workflow/model/permission decisions, fallback and measured efficiency,
then states whether docs/instructions need followup with source, target, owner,
`done_when`. No recursive JEV review or extra Stop-triggered review is introduced.

Hooks prepare one task-scoped `.agentic/jev/review-*.json` packet with exact Q/A,
native observations and explicit paths to full records. Inline questions have a
48 KiB budget; omitted questions remain in their referenced full records.
OpenCode appends the packet path to the reviewer assignment. Codex passes it as
native `SubagentStart` developer context, leaving encrypted assignments unchanged.
Reviewers must read these exact paths; ordinary search omits Git-ignored journals.
OpenCode also supplies up to 64 KiB of cleansed packet content directly, overriding
incorrect coordinator assertions that JEV records are absent.

## Real local blackbox

```sh
# Existing local CLI authentication; JEV key from OS env or this checkout's .env.
JEV_API_URL=https://jevtypesafeai.com/api/v1/decide make blackbox
# Individual hosts:
make blackbox-codex
make blackbox-opencode
make blackbox-claude
# Recheck saved execution and arithmetic without any paid requests:
make blackbox-opencode BLACKBOX_ARGS='--verify-only --run-dir /absolute/path/.agentic-blackbox/<run>'
```

Each host receives a separate temporary Git project. The built Agentic installs
`software.backend` + `software.general`, enables JEV and installs hooks. The
real CLI receives exactly **«разработай простой калькулятор на Python в одном файле»**
with no workflow flag; the one-file scope keeps every role's work short.
Following the requested OpenAI restriction, the OpenCode coordinator uses the
configured `openai/gpt-6-luna` (ChatGPT-account OAuth no longer serves `gpt-5.5`; `BLACKBOX_OPENCODE_MODEL` can override it with another
OpenAI model); JEV subagent candidates are restricted to OpenAI through
`AGENTIC_JEV_MODEL_PROVIDER=openai`. Codex has no model flag. Routing uses the same
default-versus-pin rules in tests and production, without a test-only routing override.
Global files remain unchanged. Tests run sequentially, with at most three prompts and an 8-minute limit per host (`--timeout` sets seconds), and leave projects
available for inspection. Cleansed traces/results are saved in
`.agentic-blackbox/<run>/`; `project.json` records each temporary project's path.
These targets are opt-in and paid; `make test`/CI remain offline.

For Codex trust preparation, first run:

```sh
JEV_API_URL=https://jevtypesafeai.com/api/v1/decide \
  make blackbox-codex BLACKBOX_ARGS=--prepare-only
codex -C /tmp/agentic-jev-blackbox-codex-<id>
# Review the exact five Agentic definitions in /hooks, then exit.
make blackbox-codex BLACKBOX_ARGS='--run-dir /absolute/path/.agentic-blackbox/<run>'
```

Claude runs `claude -p --output-format stream-json --verbose --permission-mode
acceptEdits --model ${BLACKBOX_CLAUDE_MODEL:-sonnet}` with a narrow
`--allowedTools` list for test commands (`python`, `node`, `npm`, `pytest`, `ruff`,
`make`, `git`, `ls`, `mkdir`, `cat`); the prompt goes to stdin. The list exists only on the
blackbox command line and is never written into the project. Project guidance
requires explicit approval for new root files (`Makefile`, `CHANGELOG.md`, …), so
the coordinator may stop and ask. On every host, when the first turn ends without a
verifiable calculator, the run sends a bounded approval reply into the same
native session, at most twice (`claude -p --resume <session>`, `opencode run --session <id>`,
`codex exec resume <thread>`) and then judges the result; no other input is
supplied. Every host also enables
Telegram against a local fake Bot API with run-local credentials
(`AGENTIC_CONFIG_DIR`) and requires `telegram_fired`. Codex runs with
`--sandbox workspace-write`; hosts that block unprivileged user namespaces
(`kernel.apparmor_restrict_unprivileged_userns=1`) cannot start its bubblewrap
sandbox, so set `BLACKBOX_CODEX_SANDBOX=danger-full-access` there. Claude also
writes an `InstructionsLoaded` recorder into the run
project's `.claude/settings.local.json`. Extra Claude checks: all nine role agents,
the `/develop-feature` command and at least one installed skill appear in the
`init` event; a `.claude/rules/` file is loaded; the Telegram `Stop` hook sends the
final answer. Requested aliases match observed transcript model ids (`haiku` ↔
`claude-haiku-…`).

Passing requires real JEV workflow selection, native workflow-load evidence,
requested/observed model agreement for the same role/session, successful CLI
completion, independent arithmetic checks and `follow_up_without_jev_call` (no
follow-up prompt sent a JEV request). `results.json` reports `jev_calls`,
`jev_input_tokens` and `follow_up_prompts` for the task. A fallback, provider error,
clarification stall or recommendation without application cannot pass.
The built-in arithmetic probe supports public Python/JavaScript calculator evaluators,
including `src/` packages with relative imports, numeric results such as `Decimal`,
domain errors that name the division by zero, and one consistent operator spelling
per run: ASCII (`- * /`), typographic (`− × ÷`) or words (`subtract`, …). JavaScript
keypad state APIs (`createCalculator` with `inputDigit`/`enterDigit`,
`chooseOperation`/`chooseOperator`, `calculate`/`equals`) are driven key by key.
Other stacks require `BLACKBOX_VERIFIER=/absolute/path/to/executable`; it receives
the project path and must independently execute calculator checks, returning JSON
`{"verified":true}` and exit zero. Agent-authored assertions are not accepted.

Native hook trust and valid host provider authorization are prerequisites. A key
for JEV does not authenticate coding models. Inspect `results.json` and the
cleansed trace for failed/blocked prerequisites. The endpoint reports token counts
but no price, so the hooks and the blackbox record `input_tokens` and
`output_tokens` only; the former `cost_usd` field and the `AGENTIC_JEV_BUDGET_FILE`
ledger were removed in 1.5.0. The R&D questions suite (`JEV_RND_SUITE=questions`)
keeps its own `JEV_RND_BUDGET_USD` estimate.
JEV spend per run is bounded by the three-prompt limit and the session gate; coding agents use their existing host quota.

## Source contracts

[Codex hooks](https://developers.openai.com/codex/hooks) define native input
replacement, approval decisions and hook trust. [OpenCode V2 plugins](https://opencode.ai/v2/docs/build/plugins/)
define prompt, tool and permission evaluation hooks. SDK 2.0.28 source confirms
the native `subagent.model` override is applied before child creation and retains
role permission checks. Ordinary tests validate both endpoint contracts with mocks;
official paid quota has not been used.

## Codex preselection

Since 1.6.0, coordinators can submit open goal/scope/complexity before encrypted spawn through the [local prepare-spawn interface](epic/preselection.md). It reuses the shared runtime and preserves profile restrictions. Restricted profiles retain the canonical role name with unconfirmed application; simple profiles support unique one-use correlation.

See the [epic contract](epic/epic_plan.md) and [gated comparative pilot](epic/pilot.md). No pilot measurements have been made.
