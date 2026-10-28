# agentic — shared rules and a quality gate for every coding agent

> One set of project rules for Claude Code, Codex and OpenCode. A quality gate runs your checks and records acceptance. The lean default adds no role team; helper agents, workflows and model routing are optional.

![Codex · real runs](https://img.shields.io/badge/Codex-real%20runs%20✓-2ea44f?logo=openai&logoColor=white)
![Claude Code · real runs](https://img.shields.io/badge/Claude%20Code-real%20runs%20✓-2ea44f?logo=anthropic&logoColor=white)
![OpenCode · real runs](https://img.shields.io/badge/OpenCode-real%20runs%20✓-2ea44f)
![Antigravity · configs](https://img.shields.io/badge/Antigravity-configs%20only-lightgrey)
![Gemini · configs](https://img.shields.io/badge/Gemini-configs%20only-lightgrey)
![Cursor · configs](https://img.shields.io/badge/Cursor-configs%20only-lightgrey)
![Kilocode · configs](https://img.shields.io/badge/Kilocode-configs%20only-lightgrey)

[![Lean profile · default](https://img.shields.io/badge/Lean%20profile-default-blue)](docs/agentic-v2-lean/README.md) [![Quality gate · checks + acceptance](https://img.shields.io/badge/Quality%20gate-checks%20%2B%20acceptance-blue)](docs/agentic-v2-lean/README.md#quality-gate) [![Company rules](https://img.shields.io/badge/Company%20rules-path%20or%20git-blue)](docs/company-rules.md) [![JEV · workflow + model routing](https://img.shields.io/badge/JEV-workflow%20%2B%20model%20routing-blue)](docs/jev-integration/README.md) [![Plain answers · ASD-STE100-based](https://img.shields.io/badge/Plain%20answers-ASD--STE100%20based-blue)](AGENTS.md#response-language) [![MCP · Context7, MemPalace, Playwright](https://img.shields.io/badge/MCP-Context7%20%7C%20MemPalace%20%7C%20Playwright-blue)](docs/mcp/README.md) [![Telegram · notifications](https://img.shields.io/badge/Telegram-notifications-blue)](docs/notifications/README.md) [![Smart upgrade](https://img.shields.io/badge/Smart%20upgrade-keeps%20your%20edits-blue)](docs/agentic-upgrade/README.md)

[Website](https://sawrus.github.io/agent-guides/) ·
[Releases](https://github.com/sawrus/agent-guides/releases) ·
[npm](https://www.npmjs.com/package/@jetrabbits/agentic) ·
[Usage guide](docs/agentic-usage.md) ·
[Reference](docs/agentic-reference.md)

![agentic coverage and benchmark report](images/coverage_scorecard.png)

---

## The problem it solves

Teams now use several coding agents at once. Each agent gets its own prompts, its own habits and its own idea of
"done". One agent runs the tests, another skips them. One agent asks before it touches production, another does
not.

**agentic gives every agent the same base:**

- 📏 **Rules are the base.** 64 rules for 16 specializations (8 software, 8 DevOps). Each rule lists items that a
  reviewer can check in a diff. A rule loads only for the files it applies to (`paths:`) or on request.
- ✅ **A gate decides "done".** When the agent stops, the quality gate runs `make test` and `make lint` (or your
  own commands) and asks for a CHANGELOG line. It records the result in `.agentic/gate/last.json`.
- 🪶 **Lean by default.** The native main session does the work, with one read-only `explorer` helper. The
  always-on context is at most 2,110 tokens on any host. `--profile team` installs the optional role team.
- 🔁 **Install once, keep in sync.** `agentic install` writes the native files of each agent. `agentic upgrade`
  keeps them current and keeps your own edits.

14 skills and 10 workflows help the agent meet the rules. Numbers come from the tree (`areas/*/*/`) and from
`python3 scripts/context_budget.py --all-selections`.

---

## Runs on the agents you already use

| | Agent | Status | Evidence |
|:-:|:--|:--|:--|
| ✅ | **Codex** | Real runs | codex-cli 0.164 · benchmark round 6, 2026-10-27 |
| ✅ | **Claude Code** | Real runs | `sonnet` · benchmark round 6, 2026-10-27 |
| ✅ | **OpenCode** | Real runs | 2.0.29 · benchmark round 4, 2026-10-24 |
| ☑️ | **Antigravity** | Configs ship | Agents, rules and workflows are installed; no recorded run yet |
| ☑️ | **Gemini** | Configs ship | Agents and workflows are installed; no recorded run yet |
| ☑️ | **Cursor · Kilocode** | Configs ship | Rules and MCP settings are installed; no recorded run yet |

"Real runs" means that the agent's own CLI ran the installed instructions and a separate grader checked the
result. Details per feature: [platform matrix](docs/agentic-reference.md#feature-support-by-platform).

---

## See agentic in action

![agentic in action](images/how_to_use_agentic.gif)

A real `agentic tui` session, recorded key by key. It selects Codex, Claude Code and OpenCode with the lean
profile, Context7, DevOps infrastructure plus backend, and a company rules directory. Then the same request runs
in the main session of all three agents inside the new project.

---

## Quick start

```bash
npx @jetrabbits/agentic@latest          # interactive installer
```

Or non-interactive, for all three verified agents:

```bash
npx @jetrabbits/agentic@latest install --project-dir . \
  --agent-os codex,claude,opencode --areas software \
  --specializations software.backend,software.general
```

Keep it current:

```bash
agentic upgrade            # new binary + refreshed project instructions, your edits preserved
```

Without npm, bootstrap the latest release binary (Linux x86_64/aarch64, macOS Intel/ARM):

```bash
curl -fsSL https://raw.githubusercontent.com/sawrus/agent-guides/main/install | bash -s -- --force
```

Or download a binary from [GitHub Releases](https://github.com/sawrus/agent-guides/releases) and run
`./agentic self-install --force`, or build from source with `make release-build && make install` (Rust toolchain).
Details: [usage guide](docs/agentic-usage.md#requirements).

---

## Guardrails

The quality gate (`.agent/gate/gate.py`) runs from native hooks in Claude Code and Codex and from a plugin in
OpenCode. Details: [quality gate](docs/agentic-v2-lean/README.md#quality-gate).

- **Acceptance record.** `.agentic/gate/last.json` stores `accepted`, `reason_code`, `head`, `pack_version` and
  `profile` for the last stop.
- **Production guard.** `kubectl`, `helm` or `oc` on a context that matches `prod` asks you first. You can add
  database hosts and your own patterns in `.agent/gate.json`.
- **Database guard.** Write or maintenance SQL on a non-local database is blocked. A connection with credentials
  from `.env` asks first. In host plan mode, every non-local database connection is blocked.
- **Secret guard.** The gate blocks access to `.env*` files and private keys, `git push --force`, and recursive
  deletes outside the project.
- **Stale checkout.** Install, upgrade and the session start warn when the checkout is older than the default
  branch on origin.

## Company rules

Keep internal standards outside this public pack. `--company-rules-path <dir>` or
`--company-rules-git <url>[#ref][:subdir]` (or the TUI step "Company rules") installs them for every host, and
`agentic upgrade` replays them. A company rule wins over a pack rule on the same topic. `replaces:` or
`--company-rules-exclude` drops the pack rule, and a duplicate report lists the overlaps. See
[company rules](docs/company-rules.md).

## Standards for the pack itself

- [Artifact standard](docs/artifact-standard.md): the acceptance contract for rules, skills, workflows and company
  rules (`ART-*` ids). `make check-artifacts` checks every automatic requirement.
- [Review regulation](docs/regulation.md): the Definition of Done for code review and design review, and the
  docs coverage rule. `make check-docs-coverage BASE=<ref>` fails when changed code has no changed docs page.

---

## Your AI team

The default `lean` profile installs one helper: `explorer`, a read-only agent for code search. The main session
runs the workflow steps itself.

`--profile team` is optional. It installs the role team: `product-owner`, `pm`, `team-lead`, `developer`, `qa`,
`analyst`, `devops-engineer`, `instruction-reviewer` and `memory-curator`. A workflow then sends each step to the
role that fits it. See [role profiles](docs/agentic-reference.md#role-profiles-all-hosts).

---

## Honest numbers

We measure instead of promising. Round 6 (2026-10-27) ran Claude Code with `sonnet` and Codex with
`gpt-6.1-terra` (codex-cli 0.164 or later). Codex cost is an API-equivalent estimate.

| Check | Result |
|:--|:--|
| Devops task T11 (Kubernetes rules), Claude Code | plain agent **0/3** · lean **3/3** |
| Core tasks T1–T7 and T10, Claude Code lean, before and after the content cleanup | **8/8** and **8/8** |
| T11 lean after the content cleanup | uncached tokens × 0.72 · cost × 0.85 |
| Lean helpers with JEV routing, Codex T6–T8 | 9/9 both · every helper on the session model · cost × 1.09 of lean |
| `reviewer` helper, T8v2 (hidden defect) | Codex 9/9 with and without it · it never ran · removed from lean |

- The rules carry the devops result: every plain T11 run missed the Kubernetes security items.
- The cleanup kept quality, but full tokens fell less than the 10% target, because cached session history
  dominates them.
- JEV stays opt-in. It gives no measured quality gain.

All numbers and earlier rounds: [round 6 results](docs/agentic-v2-lean/results.md#round-6-rules-h0-h4-h-clean-h-clean-devops-2026-10-27) ·
[comparison](docs/agentic-v2-lean/comparison.md).

---

## Learn more

- [Usage guide](docs/agentic-usage.md) and [installed CLI lifecycle](docs/agentic-lifecycle.md)
- [Reference: layout, platform matrix, install options](docs/agentic-reference.md)
- [Docs site: rules, skills and workflows per specialization](https://sawrus.github.io/agent-guides/)
- [Artifact standard](docs/artifact-standard.md) · [Review regulation](docs/regulation.md) ·
  [Company rules](docs/company-rules.md)
- [Claude Code integration](docs/claude-code/README.md) · [Telegram notifications](docs/notifications/README.md)
- [Review pipeline](docs/review-pipeline.md) · [JEV hooks and real CLI testing](docs/jev-integration/README.md)
- [Smart upgrade](docs/agentic-upgrade/README.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for authoring standards, templates and the pull request process.

## License

See [LICENSE](LICENSE) if present, or contact the maintainers.
