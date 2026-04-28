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

Telegram notifications and model checking are opt-in. If the config is absent or a plugin is disabled, the plugin returns no hooks and OpenCode continues without that behavior.

Telegram notifications use either the stored config values or these environment variables:

```text
OPENCODE_TELEGRAM_BOT_TOKEN
OPENCODE_TELEGRAM_CHAT_ID
```

Non-interactive `agentic install` defaults optional plugins to disabled when no config exists.

For OpenCode targets, `agentic` writes generated operating guidance to `.opencode/AGENTS.md`. If OpenCode is installed
alongside another agent target, root `AGENTS.md` is generated as well for the non-OpenCode target.
