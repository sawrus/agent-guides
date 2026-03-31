# agent-guides

**agentic = Agent Intelligence Configuration.**

A unified catalog of agentic specializations and the `agentic` CLI. The repository provides orchestrator-ready rules, skills, workflows, and prompts that can be installed into a target project from either a local checkout or an installed binary in `~/.local/bin`.

- [Coverage scorecard](https://claude.ai/public/artifacts/8177bc3d-3b2f-48a6-8232-47c5b02b20f3)
- [Website](https://sawrus.github.io/agent-guides/)

---

## What this is

agent-guides is a structured knowledge base for AI coding agents. Instead of writing long system prompts, you install focused, composable guidance files that agents load on demand based on the task at hand.

Each **area** (e.g., `devops/kubernetes`) provides:

| File type | Purpose | When loaded |
|:---|:---|:---|
| `AGENTS.md` | Navigation index, load order, constraints | First — always |
| `rules/*.md` | Hard constraints the agent must follow | Always, for the active spec |
| `skills/*/SKILL.md` | Technical capabilities and patterns | On demand, matching "When to load" |
| `workflows/*.md` | Orchestrated step-by-step processes | On `/command` trigger |
| `prompts/*.md` | Human copy-paste templates (EN + RU) | Reference / paste |

---

## Repository structure

```text
agent-guides/
├── areas/
│   ├── software/              # Application development
│   │   ├── general/           # Shared baseline — all software specs inherit from here
│   │   ├── backend/           # REST/GraphQL APIs, services, database access
│   │   ├── frontend/          # Components, accessibility, performance, CSS
│   │   ├── full-stack/        # End-to-end product features
│   │   ├── data-engineering/  # dbt, warehouses, pipelines, streaming
│   │   ├── mlops/             # Training, evaluation, serving, monitoring
│   │   ├── mobile/            # iOS, Android, React Native, Flutter
│   │   ├── platform/          # K8s manifests, IaC, CI/CD, secrets
│   │   ├── qa/                # Test strategy, coverage, flakiness, performance
│   │   └── security/          # Threat modeling, SAST/DAST, auth, compliance
│   └── devops/                # Platform and operations
│       ├── kubernetes/        # Cluster bootstrap, workload ops, RBAC, upgrades
│       ├── ci-cd/             # GitHub Actions, GitLab CI, quality gates, supply chain
│       ├── infrastructure/    # Terraform, Ansible, IaC standards, drift detection
│       ├── observability/     # Prometheus, Loki, Tempo, Grafana, SLOs
│       ├── sre/               # SLOs, error budgets, incidents, chaos engineering
│       ├── networking/        # Ingress, TLS, service mesh, DNS, VPC
│       ├── devsecops/         # Shift-left, SBOM, OPA/Kyverno, container hardening
│       └── database-ops/      # PostgreSQL, Redis, migrations, backup/restore
├── extensions/
│   ├── opencode/              # opencode agent definitions, commands, skills
│   ├── claude/                # Claude-specific configs
│   ├── antigravity/           # Antigravity platform configs
│   ├── codex/                 # Codex override configs
│   └── gemini/                # Gemini-specific configs
├── areas/template/            # Authoring templates — start here for new content
├── docs/                      # Setup and usage guides
├── AGENTS.md                  # Root agent guidance (loaded into every project)
└── agentic                    # CLI installer
```

---

## Quick start

### Install

```bash
npx @jetrabbits/agentic@latest
```

Alternative bootstrap (installs local binary):

```bash
curl -fsSL https://raw.githubusercontent.com/sawrus/agent-guides/main/install | bash
```

### Run

```bash
agentic
```

### Full instructions

- [CLI usage guide](docs/agentic-usage.md)
- [Installed CLI lifecycle](docs/agentic-lifecycle.md)

---

## Agents (opencode)

The `extensions/opencode/agents/` directory defines the SDLC agent team:

| Agent | Role | Mode |
|:---|:---|:---|
| `product-owner` | Value definition, scope, acceptance | primary |
| `pm` | Planning, dependencies, stakeholder comms | subagent |
| `team-lead` | Technical strategy, architecture, quality gates | subagent |
| `developer` | Implementation, tests, delivery | subagent |
| `qa` | Verification, risk classification, go/no-go | subagent |
| `designer` | UX quality, interaction design, accessibility | subagent |
| `devops-engineer` | Infrastructure, CI/CD, platform reliability | subagent |

Each agent has:
- A `vibe` — one-line personality hook.
- An `Identity` section — personality, memory, and experience.
- A `Communication Style` section — how to report, flag, and escalate.
- `Success Metrics` — measurable criteria for a well-functioning agent.

---

## What gets installed where

Running `agentic` in a target project installs guidance into the project's `.agent/` directory, making it discoverable by supported agent tools (opencode, Claude Code, Cursor, etc.).

```text
project/.agent/
├── rules/       ← constraints active for every task in this project
├── skills/      ← capabilities loaded on demand
├── workflows/   ← processes triggered by slash commands
└── prompts/     ← human-paste templates
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for authoring standards, templates, and the pull request process.

Quick checklist before opening a PR:
- [ ] Used the appropriate template from `areas/template/`.
- [ ] No `{{PLACEHOLDER}}` values remain.
- [ ] Spec map in `AGENTS.md` updated.
- [ ] Constraints in rules use imperative language.
- [ ] Prompt examples include both EN and RU blocks.
---

## License

This repository is licensed under the MIT License. See [LICENSE](LICENSE).
