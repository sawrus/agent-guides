# MEMORY — MCP context providers

Use MCP context only when it improves accuracy. Keep searches narrow.

## Context7

- Use Context7 for external framework, library, SDK, API, and setup docs.
- Resolve the exact package/framework first; ask for focused docs only.
- If Context7 is unavailable, use local `docs/**`, then official upstream docs.

## Fallback

If MCP providers are unavailable, use:

1. local `docs/**`;
2. official upstream documentation;
3. model knowledge, explicitly marked as fallback.
