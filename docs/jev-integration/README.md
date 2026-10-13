# JEV activation through Agentic

## Requirements and design

Follow-up to the R&D prototype: select JEV beside Context7 in CLI/TUI, use
the official TypeSafe API by default, persist enablement, and install the skill
in every supported environment. Removing JEV must disable future calls.
Installer and status checks make no
paid requests. Existing SDLC roles and advisory verdict boundaries remain.

Install one shared `jev` skill with a small Python HTTP helper. Keep decisions
in workflow Markdown; the Rust installer only handles enablement, server URL and
asset installation. No separate Rust evaluator or MCP server is needed.
Read the selected provider's environment variable or exact key assignment in
project `.env` at runtime, without executing the file or copying credentials.

Persist `settings.jev.enabled/api_url` in `.agentic.json`. Explicit off overrides
environment/replay. The helper checks enablement before every call; disabled
calls do not read credentials. Generated root guidance points to the shared
skill, while workflow checkpoints define questions and handling of answers.

Verification: TUI selection/deselection, URL replay, installation across
seven environments, secret exclusion, dry-run, disabled/no-request behavior,
workflow hooks, skill validation and one real hosted request through the helper.

## Local check now

From this repository, `make jev-skill-live` sends one small paid request through
the skill helper using `JEV_API_KEY` from environment or local `.env`. No
standalone `agentic jev` command is needed.

## Enable in a project

```bash
make build
./target/debug/agentic tui --no-doctor
```

Select the target project and agent environments. In the integrations menu,
select `jev` with Space and confirm with Enter. There is no server picker;
the default is **TypeSafe AI (official API)** at `https://api.typesafe.ai/v1/systemone`.
Then choose `Enter key and save in project .env`, enter the key in the masked
field and press Enter. Existing unrelated `.env` values are preserved; the key
is kept outside manifests/logs and `.env` is added to the project's `.gitignore`.
Unix file permissions are restricted to 0600. Alternatively choose the existing
environment/project `.env` option. Installation makes no paid request.
Reload the agent session after installing the skill.

CLI equivalent:

```bash
./target/debug/agentic install --project-dir /path/to/project \
  --agent-os codex,claude,gemini,opencode --areas software \
  --specializations software.backend --enable-jev --no-doctor
```

For your existing paid test gateway key, override the server when starting TUI:

```bash
./target/debug/agentic tui --no-doctor \
  --jev-api-url https://jevtypesafeai.com/api/v1/decide
```

Or set the OS environment variable:

```bash
JEV_API_URL=https://jevtypesafeai.com/api/v1/decide ./target/debug/agentic tui --no-doctor
```

The override is saved in the target project's manifest. `install` also accepts
`--jev-api-url`. Official keys come from https://console.typesafe.ai/keys and use
TYPESAFE_API_KEY. The test gateway/custom endpoint uses JEV_API_KEY. No automatic
server/credential failover occurs; redirects are disabled.

From the installed project root:

```bash
python3 .agent/skills/jev/scripts/decide.py --status
python3 .agent/skills/jev/scripts/decide.py --input /tmp/jev-request.json --dry-run
python3 .agent/skills/jev/scripts/decide.py --input /tmp/jev-request.json
```

Use [example-request.json](example-request.json) as the request file. Status
returns enabled/api_url/key_available and paid_calls=0. Dry-run shows a redacted
request. A real response has status=evaluated, typed answers and usage; uncertain
answers are handed back to the workflow role. Missing key/network/provider errors
return fallback. The helper does not generate requirements, run tests or switch
the active coding model itself.

The canonical copy is `.agent/skills/jev/`. Native discovery copies are installed
for Codex (`.agents/skills`), Claude (`.claude/skills`), Gemini (`.gemini/skills`),
OpenCode (`.opencode/skills`), Cursor (`.cursor/skills`) and KiloCode/Antigravity
(their existing Agentic skill directory). All copies use the same project flag.
`default` also supports the canonical copy through generated root guidance.

## Disable and replay

Uncheck `jev` in TUI and confirm an empty selection if desired. Or repeat the
install command with `--disable-jev`. This overrides saved selections and
`--enable-jev` in the same invocation. Existing skill files can remain, but the
helper checks the disabled flag before reading input/keys or making requests.
No MCP configuration is created or removed. Replay/upgrade preserve the URL
and enabled state. Installer precedence is CLI URL > JEV_API_URL > saved URL >
official default. Runtime helper `--api-url` / JEV_API_URL can override the saved
URL. A key alone never enables JEV; runtime AGENTIC_ENABLE_JEV=0 blocks saved
true. Standalone research can explicitly use `--enabled` without a manifest;
workflow calls require the saved flag. Saved false cannot be bypassed this way.

## Workflow behavior

The root Markdown points to the optional skill. Six workflows contain explicit
conditional checkpoints: develop-feature, develop-epic, development-cycle,
develop-feature-fullstack, feature-implementation-flow, backend-project-full-cycle.
They specify which state/question to send and which role handles the result.
The helper only transports typed decisions; policy and role ownership remain
in Markdown. All arithmetic and evidence provenance checks stay local.

Each workflow now uses maintained question objects from the installed skill's
`references/questions.json` and packet/action contracts from
`references/checkpoints.md`. This prevents one role from losing the "least
expensive sufficient" requirement or silently adding unrelated project repairs
to a routing packet. Original request, agreed scope and approval provenance
stay explicit; out-of-scope findings are separate proposals.

Scope alignment, evidence coverage, disputed review blockers, fix-loop actions,
per-criterion acceptance, epic factors and actionable post-task followups each
have their own question and owner action. JEV is skipped for deterministic
failures or missing cost telemetry. Followups name proposal IDs, source, target,
owner and done_when; process effectiveness and measured cost efficiency are
reported separately. Existing QA/sign-off/acceptance and loop limits remain.

## Per-agent model routing

With JEV enabled, the coordinator asks separately for each role invocation,
then passes the chosen available model to the host's actual spawn operation.
This includes exploration and post-task specialists. Codex defaults map fast
to `gpt-6-luna`, balanced to `gpt-6.1-sol`, frontier to `gpt-6-astra`, restricted
to its runtime catalog; no price ranking is claimed without pricing evidence.
Low confidence, missing API access or unsupported model overrides retain the
inherited parent model/reasoning (or explicit user fallback) and produce an
explicit fallback record. Former bundled role defaults are not retained
automatically. Existing SDLC agents keep their models on followups; routing
must not create extra agents beyond the workflow's six-role limit.

Bundled Codex role model/reasoning assignments are omitted during JEV-enabled
installation because Codex custom profile settings override spawn parameters.
Role instructions and sandbox remain. User-edited profiles are protected and
their explicit pins still win. Disabling JEV restores bundled defaults for
unmodified managed profiles. Record verdict, requested model and any observed
model in `docs/<feature>/model-routing.md`; a recommendation alone is not proof
of applied routing. Other hosts require an equivalent supported spawn override.

For Codex, JEV-enabled installation sets `agents.max_threads = 8` when the
project has no explicit agent limit, allowing six SDLC roles and two review
specialists. Existing project limits are preserved; a limit below six can block
this workflow. The capacity setting remains when disabling JEV. For a temporary
test override, use `codex -c agents.max_threads=8`.

## OpenCode status

The shared skill and decision checkpoints are installed for OpenCode.
Automatic per-task model application is **not implemented** there: the existing
Agent Model Mapping feature writes fixed role models at installation time.
See the skill's `references/hosts.md` for capability checks and the proposed
native adapter boundary. Until an adapter or supported native model override
is verified, report routing as `unsupported` and retain the configured model.

OpenCode's [agent documentation](https://opencode.ai/docs/agents/) describes
per-agent models, and its [SDK](https://opencode.ai/docs/sdk/) supports an explicit
model in `session.prompt`. That API capability alone does not mean Agentic
currently applies JEV choices through it. No live OpenCode routing test has
been run; an OpenCode executable is not installed in this environment.

## Verified result

`make lint`, `make test`, `make build`, skill validation and `make test-coverage`
pass. Rust line coverage is 82.37% (80% gate). A full TUI run in an isolated
temporary project verified URL override persistence, no server picker, masked
key entry, target `.env` storage, skill installation and no key in terminal or
manifest. A real hosted request through the skill returned `fast` at confidence
1.0 for the spelling fixture in the final live smoke; its reported cost was $0.000173. Official paid
quota is not available, so its request contract/key separation is tested with mocks.
