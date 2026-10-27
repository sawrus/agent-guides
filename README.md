# agentic — one AI engineering team for every coding agent

> Adaptive SDLC setup for Claude Code, Codex and OpenCode. Native agents by default; workflows, helper agents and model routing only when the task needs them.

![Codex · real runs](https://img.shields.io/badge/Codex-real%20runs%20✓-2ea44f?logo=openai&logoColor=white)
![Claude Code · real runs](https://img.shields.io/badge/Claude%20Code-real%20runs%20✓-2ea44f?logo=anthropic&logoColor=white)
![OpenCode · real runs](https://img.shields.io/badge/OpenCode-real%20runs%20✓-2ea44f)
![Antigravity · configs](https://img.shields.io/badge/Antigravity-configs%20only-lightgrey)
![Gemini · configs](https://img.shields.io/badge/Gemini-configs%20only-lightgrey)
![Cursor · configs](https://img.shields.io/badge/Cursor-configs%20only-lightgrey)
![Kilocode · configs](https://img.shields.io/badge/Kilocode-configs%20only-lightgrey)

[![Lean profile · default](https://img.shields.io/badge/Lean%20profile-default-blue)](docs/agentic-v2-lean/README.md) [![Quality gate · test + lint](https://img.shields.io/badge/Quality%20gate-test%20%2B%20lint-blue)](docs/agentic-v2-lean/README.md) [![JEV · workflow + model routing](https://img.shields.io/badge/JEV-workflow%20%2B%20model%20routing-blue)](docs/jev-integration/README.md) [![Plain answers · ASD-STE100-based](https://img.shields.io/badge/Plain%20answers-ASD--STE100%20based-blue)](AGENTS.md#response-language) [![MCP · Context7, MemPalace, Playwright](https://img.shields.io/badge/MCP-Context7%20%7C%20MemPalace%20%7C%20Playwright-blue)](docs/mcp/README.md) [![Telegram · notifications](https://img.shields.io/badge/Telegram-notifications-blue)](docs/notifications/README.md) [![Smart upgrade](https://img.shields.io/badge/Smart%20upgrade-keeps%20your%20edits-blue)](docs/agentic-upgrade/README.md)

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
  acceptance criteria — in Codex, Claude Code and OpenCode alike. The default `lean` profile keeps a short core
  and a quality gate; `--profile team` installs the full role team.
- 🛡️ **Shared guardrails.** 63 rules, 14 skills and 10 workflows for backend services, CI/CD, Kubernetes, infrastructure, security and more,
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

Installed with `--profile team`; the default `lean` profile adds only `explorer` and `reviewer`.

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

Pick the specializations your project needs — 8 software (backend, frontend, mobile, data, ML, security, …) and
8 DevOps (Kubernetes, CI/CD, observability, SRE, …).

---

## Honest numbers

We measure instead of promising. Latest round: 7 small tasks (bugfixes, a feature, a question, a scope trap, a
bugfix in a file that already fails `make lint`, a multi-module bugfix and feature), 3 runs each, 21 runs per
agent and mode. Cells show accepted runs and cost per accepted run (Codex and OpenCode: API-equivalent estimate).

| Agent | Plain agent | Lean (default) | Lean + JEV | Role team + JEV |
|:--|:-:|:-:|:-:|:-:|
| Claude Code (`sonnet`) | 18/21 · $0.092 | **21/21** · $0.095 | **21/21** · $0.097 | **21/21** · $0.073¹ |
| Codex (`gpt-5.6-terra`) | 18/21 · $0.059 | **21/21** · $0.072 | **21/21** · $0.103 | 18/21 · $0.301 |
| OpenCode (Qwen3.8-Flash-Next) | 19/21 · $0.026 | 19/21 · $0.041 | 17/21 · $0.046 | 18/21 · $0.047 |

- The plain agent is the cheapest everywhere. Every plain failure is the lint task: it left `make lint` failing.
  Lean passed that task on every Claude Code and Codex run.
- Lean + JEV accepts as many runs as lean, or fewer, and costs 1.02–1.43 × lean. It stays opt-in.
- ¹ Prompt-cache effect: the role team's long fixed prefix was already cached by earlier runs.
- Not measured yet: large multi-step tasks. The multi-module tasks did not make the plain agent fail.

All numbers, per task: [comparison](docs/agentic-v2-lean/comparison.md).

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
