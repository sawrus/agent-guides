# Agentic MCP server selection

`agentic tui` includes a dedicated `Select MCP servers to enable:` step after target agent platform selection. The fzf flow supports multi-select with Space or Tab, Enter to confirm, Esc to skip, and a `None / skip` entry for users who do not want MCP configuration generated for the current install.

The MCP menu is driven by the CLI MCP registry rather than hardcoded UI rows. The registry tracks each server's id, display title, description, security level, default disabled state, and generated config block.

Supported registry ids:

| id | Description | Security |
| --- | --- | --- |
| `opencode-docs` | OpenCode docs MCP | safe |
| `playwright` | Browser automation via Playwright MCP | sensitive |
| `kubernetes` | Kubernetes pods/logs/exec management | dangerous |
| `youtube-transcript` | YouTube transcript extraction | safe |
| `docker-mcp` | Docker MCP Gateway | dangerous |
| `context7` | Fresh library documentation | safe |
| `mempalace` | Persistent project memory | sensitive |
| `anydb` | Database access MCP | dangerous |

For non-interactive installs, set `AGENTIC_ENABLE_MCPS` to a comma-separated list of registry ids. Dangerous MCPs require explicit confirmation before config is written. In non-interactive installs, set `AGENTIC_CONFIRM_DANGEROUS_MCP=1` to enable selected dangerous MCPs; otherwise agentic skips them and reports a warning.

OpenCode config generation preserves existing unknown fields and MCP servers, preserves an existing `$schema`, and creates the default OpenCode schema when a config file is new. Re-running agentic updates only the selected MCP entries and does not remove unselected or unknown MCP entries.
