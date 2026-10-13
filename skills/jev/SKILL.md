---
name: jev
description: Use optional JEV typed decisions at SDLC workflow checkpoints for model-tier routing, evidence assessment, fix-loop actions, epic priorities and review follow-ups when enabled in the project's Agentic settings.
---

# JEV workflow decisions

Read `settings.jev` in project `.agentic.json`. If `enabled` is absent/false,
continue the standard workflow without API calls. Recheck before each call.
The default server is the official TypeSafe AI API at
`https://api.typesafe.ai/v1/systemone`. `settings.jev.api_url`
records an optional installer override. CLI `--api-url` or `JEV_API_URL` can
override the helper's server. Official TypeSafe uses TYPESAFE_API_KEY; the test
gateway/custom server uses JEV_API_KEY. The helper reads only the relevant key
from environment or project `.env`; never read,
print, copy or pass credentials as command arguments yourself.

## Invoke

Prepare a small JSON file with `state` and `questions`. Ask only the questions
specified by the current workflow checkpoint. Use this skill's helper:

```bash
python3 .agent/skills/jev/scripts/decide.py --status
python3 .agent/skills/jev/scripts/decide.py --input /tmp/jev-request.json --dry-run
python3 .agent/skills/jev/scripts/decide.py --input /tmp/jev-request.json
```

Run from project root or pass `--project-dir`. If using a native skill copy,
resolve `scripts/decide.py` relative to that skill. Python 3 standard library only.
Status and dry-run make no paid requests. Installer never tests the paid API.
Standalone R&D may explicitly use helper `--enabled` without a manifest;
workflow execution must always require the saved flag. Saved false and runtime
`AGENTIC_ENABLE_JEV=0` block even that standalone override. Server precedence:
explicit `--api-url`, JEV_API_URL, manifest api_url, official default.

Use the maintained question objects in [references/questions.json](references/questions.json)
and the packet/action contract in [references/checkpoints.md](references/checkpoints.md).
Load only the relevant contract. Copy question instructions and criteria; do
not replace "least expensive sufficient" with merely "sufficient". The
workflow selects the checkpoint and supplies its bounded evidence packet.

Example request construction (the same helper handles every checkpoint):

```python
import json
from pathlib import Path
questions = json.loads(Path(".agent/skills/jev/references/questions.json").read_text())
request = {
    "state": {
        "original_request": "Create a small FastAPI inventory CRUD scaffold without business logic",
        "agreed_scope": "One agreed resource, existing patterns, no unrelated auth redesign",
        "approval_source": "stakeholder request; resource details remain an explicit assumption",
        "role_task": "Implement the agreed scaffold and narrow tests",
        "out_of_scope_findings": [],
        "available_tiers": ["fast", "balanced", "frontier"],
        "cost_order_source": "assumed tier order; confirm with the host catalog"
    },
    "questions": {"developer_tier": questions["routing"]}
}
Path("/tmp/jev-request.json").write_text(json.dumps(request))
```

Question types: `choice` has a labelled criteria object (2–255 options),
`score` an ordered criteria array (2–10 levels), `noul` a yes/no instruction.
Multiple atomic questions can share one state. Questions are independent;
combine answers in ordinary code, not by referring to another question's answer.

## Use results

### Route each workflow agent before spawning

When JEV is enabled, make a separate routing decision before the first spawn of
each role, including repository exploration and post-task specialists. Do not
use one whole-feature verdict for all six roles. Related independent decisions
may share one API request, with a separate question and task packet per role.

Discover the host's available model catalog and supported spawn parameters.
Build a concrete tier-to-model mapping from that catalog before asking JEV:
for Codex, prefer `gpt-6-luna` for fast, `gpt-6.1-sol` for balanced and
`gpt-6-astra` for frontier, only when present in the runtime catalog. These
are defaults, not verified price comparisons. Preserve user-selected mappings
and explicit user model pins. Check host limitations in
[references/hosts.md](references/hosts.md). If a tier has no available model, exclude that
tier from the question. For `clarify`, gather missing context before delegating.

Each role packet must preserve the original request, agreed scope/non-goals
and approval provenance, and name its exact task, inputs and expected output.
Separate in-scope constraints from unrelated repository findings; do not add
maintenance to the role task to justify a more expensive model. For the developer's first spawn, use the approved
plan rather than the initial feature prompt. Apply a confident decision to the
actual host spawn model parameter, not just to text in the agent prompt. Retain
the selected role's instructions, sandbox and ownership. For Codex, use a fresh
role invocation without a full-history fork when passing a model override.

JEV-enabled installation removes bundled model/reasoning defaults from managed
Codex role templates so that explicit spawn settings can apply. User-edited
profiles remain protected; a model still pinned in such a profile takes
precedence. Do not edit a user's profile at runtime to force a verdict.

Record role/task, JEV choice/confidence, mapped model, requested spawn model,
observed model if exposed by the host, and applied/fallback/pinned/unsupported
status in `docs/<feature>/model-routing.md`. Missing runtime evidence means
observed model is unknown; never claim a recommendation was applied without
the spawn request. Below the confidence floor, use the host's inherited parent
model/reasoning or an explicit user fallback, and record which was used. The
former bundled role defaults are not automatically retained after unpinning.
Reuse the six SDLC agents for followups; do not add agents to change models.
An already-running agent keeps its model. If a changed task needs a different
tier, record `locked` and the recommendation, rather than claiming a switch.

- Inspect typed answers and distributions. Initial advisory confidence floor
  for Choice/Score is 0.9; it needs calibration before automatic decisions.
  Noul has a probability, not a separate confidence. Uncertain results go back
  to the relevant role; do not keep calling until the answer changes.
- Model tier is a recommendation. Preserve user model pins and use only
  available models when the host supports a per-invocation override.
- Check exit codes, required commands, skips, tree/diff identity and authentic
  execution sources locally first. Developer prose and a `source: ci` label
  alone do not prove tests ran. Failed/missing checks need no JEV request.
- Keep architecture sign-off, independent QA and product acceptance with their
  existing owners. Never reduce mandatory SDLC roles or change agreed criteria.
- Replan is a proposal to PO/TL. Preserve the workflow's hard retry limit and
  escalate earlier for repeated failures without a new feasible hypothesis.
- Epic scores describe factors, not arithmetic. Validate dependencies, use
  agreed effort/weights, and rank only feasible increments in code.
- Review verdicts select existing evidence-backed follow-ups; they cannot
  generate exact documentation edits or prove cost efficiency without telemetry.

Send only relevant, secret-cleansed excerpts. Helper redaction catches common
credentials, not every secret or personal datum. Do not send whole transcripts.
Use at most one call per checkpoint with unchanged evidence; batch related
atomic questions. On disabled/missing_key/network/provider/invalid-response
fallback, continue the original workflow without inventing a positive verdict.

Official API: https://docs.typesafe.ai/api. Hosted gateway:
https://jevtypesafeai.com/docs. These are distinct providers and keys.
