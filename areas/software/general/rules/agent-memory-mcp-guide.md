# Agent memory MCP guide

## Required memory source priority

For LLM agent IDE targets (Codex, Claude, OpenCode, Gemini, Antigravity, Cursor), when MemPalace MCP is configured and reachable, agents must query MemPalace memory before relying on model-only recollection.

## Agentic installer behavior

- Ask the user about Context7 MCP first.
- Ask a separate explicit follow-up question about enabling MemPalace MCP.
- If enabled, register MemPalace MCP in agent OS config so workflows can load local/project memory context.

## Runtime fallback

If MemPalace is not available at runtime, continue with standard guidance and state that memory MCP was unavailable.
