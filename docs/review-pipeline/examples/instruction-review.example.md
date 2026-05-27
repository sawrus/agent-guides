# Instruction Effectiveness Review

## Summary

The instruction set helped the task stay inside the existing extension layout and prevented the new roles from being
added to the mandatory SDLC matrix. Tool discipline was mostly strong because repository facts were discovered before
editing. The main gap was that review pipeline behavior had to be inferred from docs rather than a dedicated guidance
section. No code quality findings are included because they are outside this role's scope.

## Scores

| Category | Score 0-10 | Notes |
|---|---:|---|
| Clarity | 8 | Role boundaries were clear after reading README and SDLC rules. |
| Usefulness | 8 | Existing extension patterns made implementation straightforward. |
| Tool discipline | 8 | File inspection was targeted and avoided repeated broad loops. |
| Memory discipline | 7 | Memory rules existed, but post-task curation was not documented. |
| Ambiguity resistance | 7 | The repo lacked a review pipeline section, causing one product decision. |
| Token efficiency | 7 | Some duplicate role text is necessary for installed agents. |
| Overall | 8 | Minor instruction additions are enough. |

## Effective instructions

| Instruction | Impact | Evidence |
|---|---|---|
| Keep SDLC roles one-to-one | Prevented specialist roles from replacing core SDLC owners. | `sdlc-role-responsibilities.md` keeps the mandatory matrix unchanged. |
| Discover project guidance before implementation | Found the extension-based agent layout. | Existing files live under `extensions/*/agents`. |

## Harmful instructions

| Instruction | Problem | Evidence |
|---|---|---|
| None | No instruction directly caused task failure. | The task completed with scoped docs and tests. |

## Missing instructions

| Missing instruction | Why needed | Suggested text |
|---|---|---|
| Post-task review pipeline guidance | Future agents need to know when specialists run and where reports go. | Add a review pipeline section that lists optional roles and `.reviews/<task-id>/` output paths. |

## Redundant instructions

| Instruction | Reason |
|---|---|
| Repeated role boundaries across extension files | Required because each installed agent file must be self-contained. |

## Tool usage findings

| Tool | Calls | Useful | Waste | Notes |
|---|---:|---:|---:|---|
| `rg` | 4 | 4 | 0 | Located role and installer references quickly. |
| `sed` | 5 | 5 | 0 | Confirmed local file formats before edits. |
| `apply_patch` | 3 | 3 | 0 | Added and updated tracked files. |

## Suggested edits

### Remove

```md
None.
```

### Replace

```md
The same 7-agent team works across supported IDEs.
```

with:

```md
The same 7-agent SDLC team works across supported IDEs, with optional post-task review specialists.
```

### Add

```md
Use `instruction_reviewer` and `memory_curator` after non-trivial tasks when instruction quality or memory hygiene needs review.
```

## Estimated waste

| Metric | Estimate |
|---|---:|
| Extra tokens | 500 |
| Extra tool calls | 1 |
| Extra retries | 0 |
| Extra runtime | 2 minutes |

## Final recommendation

Minor edits

The instruction set is generally effective. Add explicit review pipeline guidance so future runs do not have to infer
how specialist agents should be used.
