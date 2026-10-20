# agentic — one AI engineering team for every coding agent

> Give Codex, Claude Code and OpenCode the same roles, rules and quality gates — installed into any project with one command.

![Codex · real runs](https://img.shields.io/badge/Codex-real%20runs%20✓-2ea44f?logo=openai&logoColor=white)
![Claude Code · real runs](https://img.shields.io/badge/Claude%20Code-real%20runs%20✓-2ea44f?logo=anthropic&logoColor=white)
![OpenCode · real runs](https://img.shields.io/badge/OpenCode-real%20runs%20✓-2ea44f)
![Antigravity · configs](https://img.shields.io/badge/Antigravity-configs%20only-lightgrey)
![Gemini · configs](https://img.shields.io/badge/Gemini-configs%20only-lightgrey)
![Cursor · configs](https://img.shields.io/badge/Cursor-configs%20only-lightgrey)
![Kilocode · configs](https://img.shields.io/badge/Kilocode-configs%20only-lightgrey)

[Website](https://sawrus.github.io/agent-guides/) ·
[Releases](https://github.com/sawrus/agent-guides/releases) ·
[npm](https://www.npmjs.com/package/@jetrabbits/agentic) ·
[Usage guide](docs/agentic-usage.md) ·
[Reference](docs/agentic-reference.md)

![agentic coverage and real-run report](images/coverage_scorecard.png)

---

## The problem it solves

Teams now use several coding agents at once. Each one gets its own prompts, its own habits and its own idea of
"done". The result is uneven: one agent writes tests, another skips them; one asks before touching infrastructure,
another does not.

**agentic gives every agent the same playbook:**

- 🧭 **One process.** A product owner, team lead, developer and QA agent hand work to each other with clear
  acceptance criteria — in Codex, Claude Code and OpenCode alike.
- 🛡️ **Shared guardrails.** 85 rules and 73 workflows for backend, frontend, DevOps, data, ML, security and more,
  loaded only when the task needs them.
- 🔁 **Install once, keep in sync.** `agentic install` writes the native files each agent expects; `agentic upgrade`
  keeps them current without overwriting your own edits.
- 🔔 **Know when work is done.** Optional Telegram messages when an agent finishes or waits for you.

---

## Runs on the agents you already use

| | Agent | Status | Evidence |
|:-:|:--|:--|:--|
| ✅ | **Codex** | Real runs | 0.163.0 · 13 pilot runs + live proof of JEV model routing, 2026-10-20 |
| ✅ | **Claude Code** | Real runs | 2.1.304 · 13 pilot runs, 2026-10-20 |
| ✅ | **OpenCode** | Real runs | 2.0.29 · 13 pilot runs, 2026-10-20 |
| ☑️ | **Antigravity** | Configs ship | Agents, rules and workflows are installed; no recorded run yet |
| ☑️ | **Gemini** | Configs ship | Agents and workflows are installed; no recorded run yet |
| ☑️ | **Cursor · Kilocode** | Configs ship | Rules and MCP settings are installed; no recorded run yet |

"Real runs" means the installed instructions were executed by that agent's own CLI and the result was checked
independently. Details per feature: [platform matrix](docs/agentic-reference.md#feature-support-by-platform).

---

## See agentic in action

![agentic in action](images/how_to_use_agentic.gif)

A real `agentic tui` session, recorded key by key: pick Codex, Claude Code and OpenCode, add Context7, JEV and
Telegram, choose DevOps infrastructure plus backend — then the same product-owner request runs in all three agents
inside the freshly installed project. Every frame is captured from a real run.

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

Other install options (curl script, release binary, build from source): [usage guide](docs/agentic-usage.md).

---

## Your AI team

| Role | What it does |
|:--|:--|
| 🎯 `product-owner` | Turns a request into scope and acceptance criteria; accepts the result |
| 🗺️ `pm` | Plans milestones and risks for larger work |
| 🏗️ `team-lead` | Designs the approach and signs off on quality |
| 💻 `developer` | Implements the change with tests |
| 🔍 `qa` | Verifies the result and gives go / no-go |
| 📐 `analyst` | Clarifies requirements, scenarios and API contracts |
| ⚙️ `devops-engineer` | Handles CI/CD, infrastructure and deployment |
| 🧹 `instruction-reviewer` · `memory-curator` | Review the run afterwards and suggest guidance fixes |

Pick the specializations your project needs — 10 software (backend, frontend, mobile, data, ML, security, …) and
8 DevOps (Kubernetes, CI/CD, observability, SRE, …).

---

## Honest numbers

We measure instead of promising. In a [39-run pilot](docs/jev-integration/epic/pilot_results.md) on small,
bounded tasks (an infra feasibility check, a code review, a CLI calculator) with a 50k-token cap per run:

- a **plain agent was the cheapest and fastest** (8 of 9 accepted, ~20k tokens) — the agentic team loads its playbook
  and starts role agents first, about 2.7× the tokens, and often hit the 50k cap on these tiny tasks;
- the agentic team pays off when you need the **same process, checks and review trail across agents and people**,
  not when you need the shortest answer to a tiny task;
- the optional [JEV](docs/jev-integration/README.md) decision service picked a fitting workflow for the coding task
  and lowered cost in some runs, but not consistently yet.

Raw, anonymized results: [pilot-results.json](docs/jev-integration/epic/pilot-results.json).

---

## Learn more

- [Usage guide](docs/agentic-usage.md) and [installed CLI lifecycle](docs/agentic-lifecycle.md)
- [Reference: layout, platform matrix, install options](docs/agentic-reference.md)
- [Claude Code integration](docs/claude-code/README.md) · [Telegram notifications](docs/notifications/README.md)
- [Review pipeline](docs/review-pipeline.md) · [JEV hooks and real CLI testing](docs/jev-integration/README.md)
- [Smart upgrade](docs/agentic-upgrade/README.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for authoring standards, templates and the pull request process.

## License

See [LICENSE](LICENSE) if present, or contact the maintainers.
