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

OpenCode config generation writes current OpenCode-compatible top-level `mcp` entries, not legacy `mcpServers`. Re-running agentic preserves existing unknown fields, preserves an existing `$schema`, updates only the selected MCP entries, and migrates any existing OpenCode `mcpServers` entries into `mcp` before removing the invalid legacy key.

Codex config generation remains TOML-based and writes `[mcp_servers.<name>]` sections in `.codex/config.toml`.
