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

On the original user prompt, JEV chooses from the workflows actually installed
in `.agent/workflows/`. The host receives context directing it to load and execute
the selected workflow with its native roles. Explicit workflow requests remain
unchanged. This is a context instruction; actual execution must be verified from
native tool evidence, not merely from JEV's recommendation.

Before creating a subagent, JEV chooses the least expensive sufficient available
model for the original task and exact role assignment. Candidates are restricted
to the models assigned by the installed project's role profiles, intersected with
the host's available catalog and known availability restrictions. An empty
intersection retains native behavior. Role title alone must not
inflate complexity. Codex uses its native model cache; OpenCode uses its runtime
catalog, capabilities and prices. Codex `PreToolUse` rewrites the native spawn
arguments; OpenCode rewrites `subagent.model`. Native role permissions remain.
Explicit tool model assignments, models written in local role Markdown, manual
local configuration changes and continuing existing children are preserved.
Inherited role models and unchanged Agentic mapper assignments are defaults that
JEV can route. Mapper state records `model_defaults`; changing a local role model
relative to that snapshot makes it a pin. Selected bundled/custom OpenCode profile
defaults are recorded in `.agent/jev/opencode-profile-defaults.json`; unchanged
profile assignments are also routable. Legacy mapper states without a snapshot
conservatively retain local model pins. To reconfigure them, back up and move
`.opencode/agent-model-mapper.state.json` out of that path, then select the mapper
in Agentic TUI and confirm the desired defaults again. Root `opencode.json` role
models also remain explicit pins. If a local configuration cannot be safely parsed
(including JSONC comments), model routing falls back without a paid request.
Production considers all active providers, not just OpenAI. Catalog visibility
means quota is unknown unless verified. Observed OpenCode HTTP auth/quota failures
exclude that model from subsequent decisions for 15 minutes (429: one minute);
no paid availability probes or unproven quota claims are made.
Bundled Codex role defaults are recorded in `.agent/jev/model-defaults.json`
and omitted from native TOML when enabled so they do not override hook decisions;
explicit models in user profiles also enter the pool and remain pinned for that role. User-edited profiles are
protected. Missing/unknown prices do not prove cheapest. Reviewer selection uses
comparable input+output catalog prices, otherwise `AGENTIC_JEV_REVIEW_MODEL` or
`settings.jev.lightweight_model`; the Codex default is available `gpt-6-luna`.

Permission evaluation can return allow/deny/ask. Explicit native denials remain
final. Automatic approval is bounded to project/system temporary paths with
sandbox preserved. Secrets, deletion, outside paths, network/escalation and
symlink escapes require native approval. Arbitrary shell commands are assessed,
but only simple provably bounded commands may be auto-approved; interpreters,
substitutions, pipes and redirects remain native approval requests. Codex Bash
PermissionRequest represents escalation/network approval and is never auto-allowed.
JEV does not execute commands or grant sandbox exemptions.

Errors, unavailable keys/catalogs, timeout (eight seconds), oversized requests,
confidence below 0.9 and duplicate in-flight events retain native behavior.
The same native event is evaluated once; no retry requests for a preferred answer.
Disabled integration makes no requests and does not read credentials.

Some Codex transports expose encrypted subagent assignments to hooks. The audit
marks `assignment_unavailable`; JEV receives original scope and role metadata,
not decrypted content. Confidence assesses capability fit, while price and quota
can remain unknown. Ambiguous capability requirements still trigger fallback.

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
| `SubagentStart` | Observation | Review packet path for `instruction-reviewer` |
| `SubagentStop` | Observation | Observed model from `agent_transcript_path` |

The Agent tool accepts only the aliases `opus`, `sonnet` and `haiku`.
Candidates are those aliases, restricted to the aliases that the selected Claude
profile assigns (`.agent/jev/model-defaults.json`). An answer that is not an alias
is never applied. `haiku` is the lightweight reviewer model. When JEV is enabled,
`model:` is left out of `.claude/agents/*.md` so the hooks can route each spawn.
An explicit `model` in the Agent call, or a `model:` that a user adds to a role
file, is a pin and is preserved. Claude does not need a hook trust review.

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
flags. Changed definitions require review again. For CLI tests use `--no-daemon`
to avoid inheriting a shared server's project configuration. OpenCode discovers
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
real CLI receives exactly **«разработай калькулятор»** with no workflow flag.
Following the requested OpenAI restriction, the OpenCode coordinator uses the
configured `openai/gpt-6-luna` (ChatGPT-account OAuth no longer serves `gpt-5.5`; `BLACKBOX_OPENCODE_MODEL` can override it with another
OpenAI model); JEV subagent candidates are restricted to OpenAI through
`AGENTIC_JEV_MODEL_PROVIDER=openai`. Codex has no model flag. Routing uses the same
default-versus-pin rules in tests and production, without a test-only routing override.
Global files remain unchanged. Tests run sequentially, with a 20-minute limit per host, and leave projects
available for inspection. Cleansed traces/results are saved in
`.agentic-blackbox/<run>/`; `project.json` records each temporary project's path.
These targets are opt-in and paid; `make test`/CI remain offline.

For Codex trust preparation, first run:

```sh
JEV_API_URL=https://jevtypesafeai.com/api/v1/decide \
  make blackbox-codex BLACKBOX_ARGS=--prepare-only
codex --no-daemon -C /tmp/agentic-jev-blackbox-codex-<id>
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
verifiable calculator, the run sends exactly one bounded approval reply into the same
native session (`claude -p --resume <session>`, `opencode run --session <id>`,
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
completion and independent arithmetic checks. A fallback, provider error,
clarification stall or recommendation without application cannot pass.
The built-in arithmetic probe supports public Python/JavaScript calculator evaluators,
including `src/` packages with relative imports, numeric results such as `Decimal`,
domain errors that name the division by zero, and one consistent operator spelling
per run: ASCII (`- * /`), typographic (`− × ÷`) or words (`subtract`, …).
Other stacks require `BLACKBOX_VERIFIER=/absolute/path/to/executable`; it receives
the project path and must independently execute calculator checks, returning JSON
`{"verified":true}` and exit zero. Agent-authored assertions are not accepted.

Native hook trust and valid host provider authorization are prerequisites. A key
for JEV does not authenticate coding models. Inspect `results.json` and the
cleansed trace for failed/blocked prerequisites. The shared `.agentic-blackbox/jev-budget.json` ledger reserves $0.02 per call,
settles reported costs, and stops before the configured $5 limit. Unknown costs
retain the reservation; it is a conservative guard, not a provider billing cap.
Existing test quota remains bounded by the agreed $5 JEV budget; coding agents use their existing host quota.

## Source contracts

[Codex hooks](https://developers.openai.com/codex/hooks) define native input
replacement, approval decisions and hook trust. [OpenCode V2 plugins](https://opencode.ai/v2/docs/build/plugins/)
define prompt, tool and permission evaluation hooks. SDK 2.0.28 source confirms
the native `subagent.model` override is applied before child creation and retains
role permission checks. Ordinary tests validate both endpoint contracts with mocks;
official paid quota has not been used.
