# Agentic Token-Minimization Upgrade

This feature reduces the amount of guidance copied into target projects while making future `agentic` reruns safer.

## Managed Files

After installation, `agentic` writes `.agentic.json` in the target project root. The file records:

- selected agent OS targets, areas, and specializations;
- source repository and checkout path;
- every file managed by `agentic`;
- each managed file's source path and SHA-256 hash;
- skipped files from the latest rerun.

When `agentic` runs again in a project with `.agentic.json`, it updates only files listed in that manifest. If a managed file hash no longer matches the last `agentic` write, the file is treated as user-modified and is skipped.

## Generated Markers

Every copied or generated file is marked internally:

- Markdown files receive `agentic` metadata in YAML front matter.
- TypeScript, shell, TOML, Python, YAML, CSS, and similar text formats receive a valid comment.
- JSON files receive an `_agentic` metadata object because JSON does not allow comments.

The marker includes `generated_by: agentic`, the source path, and `https://github.com/sawrus/agent-guides`.

## OpenCode Optional Plugins

When installing for OpenCode, `agentic` writes optional plugin state to:

```text
~/.config/agentic/opencode-plugins.json
```

Interactive installs ask whether to enable Telegram notifications and model checking. Non-interactive installs default optional plugins to disabled when no config exists.

The OpenCode plugins read this config at startup and return no hooks when disabled. Telegram credentials can also be supplied through:

```text
OPENCODE_TELEGRAM_BOT_TOKEN
OPENCODE_TELEGRAM_CHAT_ID
```

## Context7

`agentic` adds Context7 MCP configuration for known project-level formats:

- `opencode.json`
- `.opencode/opencode.json` for backward compatibility with existing generated OpenCode extension config
- `.codex/config.toml`
- `.mcp.json` for Claude Code project-scoped MCP servers
- `.cursor/mcp.json`
- `.gemini/settings.json`

Interactive installs ask whether to enable Context7. If enabled, the Context7 API key is optional. Empty keys keep the install usable with default Context7 limits or rule-only fallback behavior. Non-interactive installs enable Context7 only when `CONTEXT7_API_KEY` is already set. Generated guidance requires agents to use Context7 for framework, SDK, library, and API documentation before relying on model memory when the project config is present.

Directory copies are processed in batches so large specialization installs avoid spawning a separate marker/manifest process for every copied file. Manifest protection still applies: existing unmanaged files are skipped on rerun, user-modified managed files are skipped, and new generated files can be added by newer `agentic` versions.

## Full-Stack Skill Budget

`areas/software/full-stack/skills` is capped at six core skills:

- `api-design-principles`
- `api-patterns`
- `app-builder`
- `backend-developer`
- `blackbox-test`
- `prompt-project-planner`

This keeps task-specific context smaller while preserving workflow coverage.

## Quality Audit

`scripts/assess_area_quality.py` scores every specialization by environment. It writes:

- `reports/area-quality.json`
- `reports/area-quality.md`

The audit is warn-first by default. A strict threshold can be enabled through its CLI flags, but project verification should invoke it through Makefile targets.
