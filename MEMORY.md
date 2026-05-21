# MEMORY — MCP context providers

Use MCP context only when it improves accuracy. Keep searches narrow.

## Context7

- Use Context7 for external framework, library, SDK, API, and setup docs.
- Resolve the exact package/framework first; ask for focused docs only.
- If Context7 is unavailable, use local `docs/**`, then official upstream docs.

## MemPalace

MemPalace stores project memory by wing. The current project wing is the sanitized project directory basename. Cross-project Markdown knowledge belongs in `shared_docs`.

### Cheap search pattern

Do not run broad startup searches. Search only for the task at hand:

```json
mempalace_search({
  "query": "short exact keywords",
  "wing": "<current_project_wing>",
  "limit": 3,
  "max_distance": 0.55
})
```

Rules:

- Keep `query` short; put background in `context` only if needed.
- Use `wing` whenever you know it.
- Use `limit: 3` by default; raise it only when evidence is thin.
- Use `max_distance` around `0.4-0.6` for precise fact lookup.
- Search `shared_docs` only for reusable docs or cross-project behavior.
- Call `mempalace_list_wings` or `mempalace_list_rooms` only when the wing or room is unknown.
- Add `room` only after confirming the room name.

### Writing facts

Store only durable, self-contained facts:

- architecture decisions and rationale;
- domain rules and API/data contracts;
- non-obvious integrations or constraints;
- known issues, bottlenecks, and mitigations;
- team conventions not already captured in `docs/**`.

Store one fact per call, tagged with project/module/domain nouns. Write project facts to the current project wing. Write to `shared_docs` only when the knowledge is intentionally reusable across projects.

## Fallback

If MCP providers are unavailable, use:

1. local `docs/**`;
2. official upstream documentation;
3. model knowledge, explicitly marked as fallback.
