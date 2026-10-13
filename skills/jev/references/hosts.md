# Applying model choices by host

Loading a skill or writing a model name in a role prompt does not change the
host's model. Verify the supported tool signature and observe the runtime.
Never edit shared live agent configuration per request: concurrent tasks can
race and user model pins/permissions can be lost.

## Codex

Use an explicit `model` on the actual role spawn, without a full-history fork.
JEV-enabled Agentic installation omits bundled role model/reasoning defaults;
user-edited profiles remain pinned/protected. Observed prototype runs confirmed
`gpt-6-astra` in the spawn and child turn metadata for TL and Developer, but the
inventory workflow was stopped and is not evidence of accepted feature delivery
or cost savings. Low-confidence choices inherit the parent model/reasoning.

## OpenCode

Current Agentic installs the JEV skill/checkpoints, but does not install a
runtime OpenCode model-routing adapter. `agent-model-mapper` chooses fixed
role models at installation; it does not apply a JEV answer per task.
Bundled profiles and user mappings can pin `agent.<role>.model`.

For the installed OpenCode version, inspect its actual task/subagent signature.
Do not assume Codex's `model` parameter exists there. Without a supported
override or a tested adapter, record the JEV model recommendation as
`unsupported` and use the existing configured role model. Other checkpoints
can still invoke the Python helper normally.

The official SDK documents `session.prompt` with
`model: {providerID, modelID}`. A potential thin native custom tool could ask JEV
through the shared helper, then invoke a child session with that model and the
original role. This is a design option, not an installed capability. Before
shipping, it must preserve parent task authorization, role tool permissions,
parent/child session linkage, cancellation, user pins and real observed model
metadata. It must not run a second unbounded workflow or replace the manual
install-time mapper. Runtime task routing needs a version-specific smoke test.

Primary sources:
- https://opencode.ai/docs/agents/ — fixed per-agent model preferences.
- https://opencode.ai/docs/sdk/ — explicit model on session.prompt.
- https://opencode.ai/docs/plugins/ — native custom tools and hooks.
- https://opencode.ai/v2/docs/tools/ — configured subagent invocation; inspect
  the actual installed version rather than assuming a model override.

## Other hosts

Apply the same supported-override and observed-model contract. Skill installation
alone does not establish model routing. If the host cannot select a model for a
role invocation, use the existing model and record `unsupported`; scope,
evidence, loop, priority and review decisions remain independent of routing.
