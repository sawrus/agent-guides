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

Telegram notifications and agent model mapping are opt-in. Interactive `agentic install` and `agentic tui` ask for OpenCode plugin selection whenever `opencode` is selected. The menu uses readable labels (`Telegram Notifications` and `Agent Model Mapping`) while keeping the stored internal ids `telegram-notification` and `agent-model-mapper`. The answer rewrites this config. During manifest-based upgrade/re-install sync, existing plugin settings are kept so automated refreshes do not open prompts. If the config is absent or a plugin is disabled, the plugin returns no hooks and OpenCode continues without that behavior.

When `telegram-notification` is selected interactively, `agentic` asks for `botToken` and `chatId` and stores them in the target project's `.agentic.json`:

```text
settings.opencode_plugins.telegram.botToken
settings.opencode_plugins.telegram.chatId
```

The runtime plugin reads credentials from the project `.agentic.json`; it does not read Telegram credentials from environment variables. This file stores credentials in plaintext, so do not commit a Telegram-enabled `.agentic.json` to public repositories.

Non-interactive `agentic install` defaults optional plugins to disabled when no config exists.

`agent-model-mapper` reads roles from target `.opencode/agents/*.md` and discovers model names from `~/.config/opencode/opencode.json`, then adds models from active providers in `~/.local/share/opencode/auth.json` using non-deprecated entries in `~/.cache/opencode/models.json`. When enabled, interactive `agentic install`/`agentic tui` prompts for a main and fallback model per role, using `fzf` as a dropdown picker when available, and writes `.opencode/opencode.json` only after a Confirm action. OpenCode startup never opens `fzf` or waits for model input because no mapper runtime plugin is shipped or registered.

Agentic also ships reusable OpenCode model profiles in:

```text
extensions/opencode/profiles/
```

The current profiles are `OpenAI Model Profile` (`openai/opencode.json`) and `GitHub Copilot Model Profile` (`githubcopilot/opencode.json`). They appear in the same optional OpenCode selection menu as the plugin choices. Selecting one merges its agent model mapping into `.opencode/opencode.json`; later MCP configuration is merged on top, so profile selection does not block future MCP sections.

Selecting `none` applies no model profile and does not copy the baseline `extensions/opencode/opencode.json` just for profile selection. If OpenCode MCPs, Telegram notifications, or agent model mapping are selected, `agentic` may still create or update `.opencode/opencode.json` for those explicit options.

For MCP servers, OpenCode uses top-level `mcp` entries. Agentic migrates legacy `mcpServers` in OpenCode configs to `mcp` and removes the invalid key.

For OpenCode targets, `agentic` writes generated operating guidance to `.opencode/AGENTS.md`. If OpenCode is installed
alongside another agent target, root `AGENTS.md` is generated as well for the non-OpenCode target.
