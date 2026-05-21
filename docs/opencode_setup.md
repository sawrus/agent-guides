# OpenCode setup

## Configuration

The main OpenCode configuration file is located at:

```text
~/.config/opencode/opencode.json
```

## Authentication

### Auth files

OpenCode stores authentication data in two locations:

| Path | Description |
|------|-------------|
| `~/.config/opencode/` | Plugin-level credentials (for example, `antigravity-accounts.json`) |
| `~/.local/share/opencode/auth.json` | Primary provider tokens (OpenAI, Google, and others) |

## Notes

- Back up credentials before machine migration.
- Keep auth files out of version control.
- Prefer least-privilege API keys for automation.

## Agentic optional plugins

When `agentic` installs the OpenCode extension, it configures optional plugins in:

```text
~/.config/agentic/opencode-plugins.json
```

Telegram notifications and agent model mapping are opt-in. Interactive `agentic install` and `agentic tui` ask for OpenCode plugin selection whenever `opencode` is selected; the answer rewrites this config. During manifest-based upgrade/re-install sync, existing plugin settings are kept so automated refreshes do not open prompts. If the config is absent or a plugin is disabled, the plugin returns no hooks and OpenCode continues without that behavior.

Telegram notifications read credentials from environment variables only:

```text
OPENCODE_TELEGRAM_BOT_TOKEN
OPENCODE_TELEGRAM_CHAT_ID
```

Non-interactive `agentic install` defaults optional plugins to disabled when no config exists.

`agent-model-mapper` reads roles from target `.opencode/agents/*.md` and discovers model names from `~/.config/opencode/opencode.json`, falling back to a built-in list only when that file has no model names. When enabled, interactive `agentic install`/`agentic tui` prompts for a main and fallback model per role, using `fzf` as a dropdown picker when available, and writes `.opencode/opencode.json` only after confirmation. OpenCode startup never opens `fzf` or waits for model input; the runtime plugin only reports whether install-time mapping is complete.

For OpenCode targets, `agentic` writes generated operating guidance to `.opencode/AGENTS.md`. If OpenCode is installed
alongside another agent target, root `AGENTS.md` is generated as well for the non-OpenCode target.
