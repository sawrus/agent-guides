# agent-guides

![agent-guides · Coverage & Efficiency Report](images/coverage_scorecard.png)

A unified catalog of Agentic specializations and the `agentic` CLI. The repository provides orchestrator-ready rules,
skills, workflows, and prompts that can be installed into a target project from either a local checkout or an installed
binary in `~/.local/bin`.

- [coverage score card](https://claude.ai/public/artifacts/8177bc3d-3b2f-48a6-8232-47c5b02b20f3)

---

## Repository structure

```text
agent-guides/
├── areas/
│   ├── software/
│   │   ├── general/          # Cross-cutting rules and workflows (always useful to include)
│   │   ├── backend/          # Backend service development
│   │   ├── frontend/         # Frontend/UI development
│   │   ├── full-stack/       # Full-stack with layered architecture focus
│   │   ├── data-engineering/ # dbt, warehouses, pipelines
│   │   ├── mlops/            # Model training, evaluation, deployment
│   │   ├── mobile/           # iOS / Android / React Native
│   │   ├── platform/         # Infra, Terraform, K8s, CI/CD, incidents
│   │   ├── qa/               # Test strategy, flakiness, performance, coverage
│   │   └── security/         # Scans, threat modeling, secret rotation, compliance
│   └── devops/
│       ├── kubernetes/       # Cluster bootstrap, workload ops, RBAC, upgrades
│       ├── ci-cd/            # GitHub Actions, GitLab CI, quality gates, supply chain
│       ├── infrastructure/   # Terraform, Ansible, IaC standards, drift detection
│       ├── observability/    # Prometheus, Loki, Tempo, Grafana, SLO tracking
│       ├── sre/              # SLOs, error budgets, incidents, chaos engineering
│       ├── networking/       # Ingress, TLS, service mesh, DNS, VPC design
│       ├── devsecops/        # Shift-left, SBOM, OPA/Kyverno, container hardening
│       └── database-ops/     # PostgreSQL, Redis, migrations, backup/restore
├── extensions/
│   ├── opencode/             # opencode commands, agents, skills, plugins
│   ├── claude/               # Claude-specific configs
│   └── ...
├── docs/                     # Setup guides, design docs
├── agentic                   # Main CLI / installer
├── agentos-install.sh        # Deprecated compatibility wrapper that forwards to agentic
└── AGENTS.md                 # Root agent guidance (loaded into every project)
```

Each specialization follows a consistent layout:

```text
<specialization>/
├── AGENTS.md          # Specialization-specific agent guidance
├── rules/             # Constraints and conventions (always loaded)
├── skills/            # Technical capabilities (loaded on demand)
├── workflows/         # Orchestrated step-by-step processes (loaded on /command)
└── prompts/           # Human-copy-paste templates (bilingual EN + RU)
```

---

## Installed CLI lifecycle

The new lifecycle is centered around the installed `agentic` binary.

### XDG directories

`agentic` uses XDG-compatible defaults:

- Config home: `${XDG_CONFIG_HOME:-$HOME/.config}`
- Data home: `${XDG_DATA_HOME:-$HOME/.local/share}`
- Config directory: `~/.config/agentic`
- Config file: `~/.config/agentic/config`
- Knowledge base data directory: `~/.local/share/agentic`
- Knowledge base checkout: `~/.local/share/agentic/repo`

The config file currently stores the selected theme:

```ini
theme=auto
```

Supported values are `auto`, `dark`, and `light`.

### Repo resolution modes

`agentic` supports two repository source modes:

1. **Dev mode**: when you run `agentic` from a real `agent-guides` checkout and the script can find sibling
   `areas/`, `extensions/`, and `AGENTS.md`, it uses the local repository directly.
2. **Installed mode**: when the binary is installed to a standalone location such as `~/.local/bin/agentic`, it uses
   `~/.local/share/agentic/repo` as its knowledge base checkout.

### First-run bootstrap clone

In installed mode, the first command that needs repository data automatically bootstraps the knowledge base checkout by
running:

```bash
git clone https://github.com/sawrus/agent-guides.git ~/.local/share/agentic/repo
```

After cloning, `agentic` validates that the checkout contains:

- `areas/`
- `extensions/`
- `AGENTS.md`

Commands that auto-bootstrap when needed:

- `agentic list ...`
- `agentic install ...`
- `agentic tui`
- `agentic upgrade`

### Upgrade flow

To refresh the installed knowledge base checkout, run:

```bash
agentic upgrade
```

Behavior:

- If `~/.local/share/agentic/repo` does not exist yet, `agentic upgrade` performs the initial clone.
- If the checkout already exists, `agentic` runs:

```bash
git -C ~/.local/share/agentic/repo pull --ff-only
```

In dev mode, `upgrade` targets the active local checkout that `agentic` resolved next to the script.

---

## Installation

### Run directly from a local checkout

```bash
./agentic
```

Default behavior:

- In an interactive terminal: starts TUI mode
- In non-interactive mode (CI/pipe): prints usage and exits with code `1`

### Self-install the standalone binary

```bash
./agentic self-install
```

By default this installs the executable to:

```text
~/.local/bin/agentic
```

The self-install report also shows:

- installed binary path
- config directory
- knowledge base repository directory

Use `--force` to overwrite an existing binary:

```bash
./agentic self-install --force
```

Or install into a custom bin directory:

```bash
./agentic self-install --bin-dir /custom/bin
```

### Example HTTP install flow

```bash
curl -fsSL https://raw.githubusercontent.com/sawrus/agent-guides/main/agentic -o /tmp/agentic && bash /tmp/agentic self-install
```

Homebrew distribution is still planned separately.

### Deprecated wrapper

A backward-compatible `agentos-install.sh` wrapper remains in the repository for now, but it only forwards to
`agentic`. New documentation and user-facing commands should use `agentic`.

---

## CLI commands

### TUI mode

```bash
agentic tui
```

Launches a guided terminal UI to select:

- theme (`auto|dark|light`)
- project directory
- one or more agent OS targets
- one or more areas and specializations

Theme behavior:

1. default theme is `auto`
2. if `~/.config/agentic/config` exists, its `theme=` value is loaded
3. `--theme` overrides the config for the current run
4. when the TUI saves a user-selected theme, it is persisted back to the config file

TUI uses `fzf` for hotkeys (Up/Down + Space + Enter). If `fzf` is missing, the script:

1. asks permission to auto-install it (Linux: `apt/dnf/yum/pacman/zypper/apk`; Windows Git Bash: `winget/choco/scoop`)
2. falls back to index-based menus if install is declined or fails

### Install guidance into a project

```bash
agentic install \
  --project-dir /path/to/your-project \
  --agent-os opencode,codex \
  --areas software \
  --specializations software.general,software.backend
```

### List available options

```bash
agentic list agentos
agentic list areas
agentic list specs --area software
```

### Upgrade the local knowledge base checkout

```bash
agentic upgrade
```

### Common examples

```bash
agentic self-install
agentic install --project-dir /tmp/demo --areas software --specializations software.backend
agentic tui
agentic upgrade
```

---

## Install TUI dependency (`fzf`)

You can install `fzf` manually before running TUI.

Linux:

```bash
# Ubuntu / Debian
sudo apt-get update && sudo apt-get install -y fzf

# Fedora / RHEL
sudo dnf install -y fzf
# or
sudo yum install -y fzf

# Arch
sudo pacman -Sy --noconfirm fzf

# openSUSE
sudo zypper --non-interactive install fzf

# Alpine
sudo apk add --no-cache fzf
```

macOS:

```bash
brew install fzf
```

Windows (run from Git Bash):

```bash
winget install --id junegunn.fzf -e
# or
choco install fzf -y
# or
scoop install fzf
```

---

## What gets installed where

The CLI copies selected rules, skills, workflows, and prompts into the target project. For multi-value `--agent-os`,
assets are installed for each selected target (plus shared `.agent/*` paths via `agents` compatibility).
Destination directories per agent type:

| Agent OS   | rules             | skills             | workflows            | prompts          |
|------------|-------------------|--------------------|----------------------|------------------|
| `default`  | `.agent/rules`    | `.agent/skills`    | `.agent/workflows`   | `.agent/prompts` |
| `opencode` | `.opencode/rules` | `.opencode/skills` | `.opencode/commands` | _(skipped)_      |
| `cursor`   | `.cursor/rules`   | `.cursor/skills`   | _(skipped)_          | _(skipped)_      |
| `claude`   | `.agent/rules`    | `.agent/skills`    | `.agent/workflows`   | `.agent/prompts` |

In addition, the `extensions/<agent-os>/` directory is copied to `.<agent-os>/` in the target project (for example,
`extensions/opencode/` → `.opencode/`).

An `AGENTS.md` is generated at the root of the target project, assembled from:

- root `AGENTS.md` (shared guidance)
- each selected specialization's `AGENTS.md`

---

## `general` specialization

`general` contains cross-cutting rules and workflows applicable to any software project regardless of stack:

- **Rules:** git workflow, code style, Makefile conventions, Docker Compose, CI/CD, linting, SDLC methodology, role
  responsibilities, README synchronization (`readme-sync-guide.md`)
- **Workflows:** `/dev` (development cycle), `/code-review`, `/project-setup`

**Recommendation:** always include `general` alongside any specialization:

```bash
--specializations software.general,software.backend
```

When `general` is installed, its rules are available to all specialization workflows. Each specialization is designed to
be standalone (does not assume `general` is present), but combining them avoids re-stating cross-cutting conventions in
each specialization.

---

## Workflow format

Every workflow file follows this schema:

```yaml
---
name: <workflow-name>
type: workflow
trigger: /<command>          # Invocation command (e.g. /develop-feature)
description: <one sentence>
inputs: [ ... ]
outputs: [ ... ]
roles: [ subagents used ]
execution:
  initiator: <common-sdlc-role> # one of: product-owner|pm|team-lead|developer|qa|designer
related-rules: [ rule files referenced in steps ]
uses-skills: [ skills loaded during this workflow ]
quality-gates: [ exit criteria ]
---

## Steps

### 1. <Step Name> — `@owner`
- **Input:** ...
- **Actions:** ...
- **Output:** `<artifact>`
- **Done when:** ...

## Iteration Loop
...

## Exit
...
```

Workflows are designed for the **orchestrator agent**: they provide explicit per-step ownership (`@role`), inputs,
outputs, and done-criteria. Technical details are referenced via `uses-skills` — agents load skill files only when a
step requires them, minimizing token consumption. `execution.initiator` sets the subagent start role for the mandatory
repository-exploration phase using the common SDLC role taxonomy.
