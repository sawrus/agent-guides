# JEV questions rework

## User-facing behavior

JEV hooks ask three questions. They now carry a rubric and the facts JEV needs, and no test-case wording.

- **Workflow.** Options are the installed `type: workflow` files plus `native` and `clarify`. Each option shows the
  description, inputs → outputs, roles and the new frontmatter field `selection.use-when`. The single catch-all
  workflow (`selection.general: true`, today `software/general/development-cycle-workflow`) is marked `GENERAL.`.
  `native` and `clarify` keep the host's native behavior.
- **Model.** JEV picks a tier: `fast`, `balanced`, `frontier` or `clarify`. The hook maps the tier to a model per host.
  Without a confident tier the subagent gets its role default, on Codex, OpenCode and Claude.
  - On OpenCode without usable catalog prices, tiers come from a shipped tier map (`cost_source: tier_map`). Role
    defaults come from the role's tier, unless the profile names a catalog model. A default OpenCode install now
    routes models.
  - A Codex spawn with an encrypted assignment is not sent to JEV (`fallback/assignment_unavailable`); the role
    default applies.
- **Permission.** JEV sees target paths, sizes and command shape, never file content. The requesting role is shown only
  when it is an installed role agent.

Every workflow now declares when it fits:

```yaml
agent: developer
selection:
  general: false
  use-when: "The request asks to restructure existing backend code without changing its behaviour."
  avoid-when: "The request asks for new behaviour."   # optional
```

## Acceptance criteria

- Every `areas/**/workflows/*.md` has a `selection` block with a boolean `general` and a quoted `use-when` of at most
  300 characters; `avoid-when` is optional and follows the same limit.
- At most one workflow per top-level area has `general: true`.
- `make lint-content` fails on a missing or invalid block; `areas/template/workflow.tmpl.md`, `areas/template/GUIDE.md`
  and `CONTRIBUTING.md` describe the field.
- `use-when` describes a kind of request by purpose, inputs and outputs. It does not copy a test prompt.

## Operational constraints

- Write `use-when` for routing, not for marketing: name the request that this workflow serves, and use `avoid-when` for
  the closest request that belongs to another workflow (for example, project setup versus building a program in an
  empty repository).
- Confidence thresholds are per question in `.agentic.json` (`settings.jev.thresholds`, range 0.5–1, default 0.9).
  The permission floor is safe only because `auto_allow_eligible` still blocks automatic approval outside the bounded
  project paths.
- `.agent/jev/model-defaults.json` is version 2 (`roles` and `tiers`). Reinstall rewrites it; the hook still reads the
  old flat file without tier routing.
- OpenCode reads its tier map from `.agent/jev/opencode-model-tiers.json` (source `extensions/opencode/model-tiers.json`).
  Its model ids are `provider/id`; a content test checks them, and the Codex ids, against frozen host catalogs. Change
  the map and the Codex role defaults together: the OpenCode role tiers must mirror the Codex ones.
- Details: `docs/jev-integration/README.md`, section "Questions, tiers and records".
