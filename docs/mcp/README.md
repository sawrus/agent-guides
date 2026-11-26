---
covers:
  - src/mcp.rs
  - src/legacy.rs
---

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
| `anydb` | Database access MCP | dangerous |

For non-interactive installs, set `AGENTIC_ENABLE_MCPS` to a comma-separated list of registry ids. Dangerous MCPs require explicit confirmation before config is written. In non-interactive installs, set `AGENTIC_CONFIRM_DANGEROUS_MCP=1` to enable selected dangerous MCPs; otherwise agentic skips them and reports a warning.

OpenCode config generation writes current OpenCode-compatible top-level `mcp` entries, not legacy `mcpServers`. Re-running agentic preserves existing unknown fields, preserves an existing `$schema`, updates only the selected MCP entries, and migrates any existing OpenCode `mcpServers` entries into `mcp` before removing the invalid legacy key.

Codex config generation remains TOML-based and writes `[mcp_servers.<name>]` sections in `.codex/config.toml`. When any selected Codex MCP requires outbound network access, generated config also writes `[sandbox_workspace_write] network_access = true`. Codex MCP entries use non-interactive `npx -y` package startup where relevant and include startup/tool timeouts for first-run reliability.

When `kubernetes` is selected, `agentic` checks whether `kubectl version` succeeds. If it does not, install continues and the final report warns with the official kubectl setup guide: <https://kubernetes.io/docs/tasks/tools/>.

When `docker-mcp` is selected, generated MCP server names use `docker` instead of the older `MCP_DOCKER`. `agentic` checks whether `docker mcp --version` succeeds. If it does not, install continues and the final report warns with Docker setup links: <https://docs.docker.com/get-started/get-docker/> and <https://docs.docker.com/ai/mcp-catalog-and-toolkit/>.

## Removed: MemPalace

agentic v9.0.0 removed the `mempalace` MCP integration. `AGENTIC_ENABLE_MEMPALACE`, `AGENTIC_MEMPALACE_SETUP`, and
`AGENTIC_MEMPALACE_TIMEOUT_SECONDS` have no effect. A manifest that still lists `mempalace` in
`settings.mcp_integrations` gets a warning, and the entry is dropped. `agentic install` and `agentic upgrade` remove
the `mempalace` server entries that the manifest records as agentic-owned (`config_owned_keys`), and a
`.mempalaceignore` file that agentic wrote and the user did not edit. Other entries stay; `UPGRADE.md` lists them for
manual removal.
