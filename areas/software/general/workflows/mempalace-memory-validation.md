---
name: mempalace-memory-validation
type: workflow
trigger: /mempalace-memory-validation
description: Validate that agent workflows consume MemPalace MCP memory when available.
inputs:
  - configured_agent_os
  - workflow_name
outputs:
  - memory_mcp_validation_report
roles:
  - "@qa"
execution:
  initiator: qa
---

## Steps

1. Verify target agent configuration includes `mempalace` MCP server.
2. Start workflow (for example `/develop-feature`) with test memory entries pre-seeded.
3. Confirm produced output includes facts from MemPalace memory.
4. Record fallback behavior when MemPalace is unreachable.
