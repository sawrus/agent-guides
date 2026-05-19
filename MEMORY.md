# MEMORY — MCP context providers

Guidance for using MemPalace and Context7 MCP servers across all agent sessions.

---

## Provider roles

| Provider | Purpose |
|---|---|
| **MemPalace** | Project-specific knowledge: architecture decisions, domain rules, conventions, known issues, integration contracts |
| **Context7** | Framework, library, SDK, and API reference documentation |

Use both when available. They are complementary, not interchangeable.

---

## Context7

- Use Context7 for framework, library, SDK, API, and setup documentation before relying on model memory.
- Resolve the library or framework identity first, then request focused docs for the exact task and version when version matters.
- If Context7 is unavailable, state that explicitly and fall back to local docs or official project documentation.

---

## MemPalace

### Loading context — session start

Query MemPalace **before** reading any source files. Orientation queries to run at the start of every session:

```
mempalace_search({ "query": "project architecture decisions" })
mempalace_search({ "query": "domain entities and relationships" })
mempalace_search({ "query": "known constraints and non-negotiables" })
```

Before touching any subsystem, query for accumulated knowledge about it:

```
mempalace_search({ "query": "<module or service name> design decisions" })
mempalace_search({ "query": "<module or service name> known issues" })
```

### Writing facts — when to store

Store a fact **immediately** when you discover or confirm any of the following. Do not wait until the end of the session — subsequent steps in the same session benefit from facts stored earlier.

| Trigger | What to store |
|---|---|
| Architecture decision made or confirmed | Decision, alternatives considered, rationale |
| Non-obvious module dependency or integration point | What connects to what and why |
| Business rule or domain constraint clarified | The rule in plain language, where it is enforced |
| Recurring bug pattern or root cause identified | Pattern description, affected area, mitigation |
| API contract or data shape locked down | Shape, version, owning service |
| Performance characteristic or known bottleneck noted | Where, measured or estimated, relevant thresholds |
| Convention or team agreement not captured in docs | The agreement and its scope |
| Environment or deployment constraint discovered | What the constraint is and which target it affects |

### Writing facts — examples

```
mempalace_store({
  "type": "architecture_decision",
  "title": "Auth uses JWT with 15-min expiry, refresh via Redis",
  "body": "Decided in task TASK-88. Rationale: stateless verification at API gateway; Redis holds refresh token allowlist for revocation support.",
  "tags": ["auth", "jwt", "redis", "architecture"]
})
```

```
mempalace_store({
  "type": "domain_rule",
  "title": "Orders cannot transition from CANCELLED back to any active state",
  "body": "Enforced in OrderStateMachine.apply(). No UI path or API endpoint bypasses this; confirmed with product owner in TASK-102.",
  "tags": ["orders", "state-machine", "domain-rule"]
})
```

```
mempalace_store({
  "type": "known_issue",
  "title": "ReportService N+1 on invoice line items — not yet fixed",
  "body": "Affects reports with >50 invoices. Tracked in TASK-119. Workaround: batch fetch via InvoiceRepository.findByReportId().",
  "tags": ["reporting", "performance", "n+1"]
})
```

```
mempalace_store({
  "type": "convention",
  "title": "Feature flags go through FeatureToggleService — no direct env checks in domain code",
  "body": "Established to keep domain layer portable. All flag reads must go through FeatureToggleService.isEnabled(flag, context).",
  "tags": ["conventions", "feature-flags"]
})
```

### Quality bar for stored facts

- **Concrete, not vague.** "Auth uses JWT" is a fact. "Auth is secure" is not.
- **Self-contained.** The fact must make sense without the surrounding chat context.
- **Tagged for retrieval.** Include module names, domain nouns, and problem-type tags.
- **One fact per store call.** Do not bundle multiple unrelated facts into one entry.

---

## Fallback order

When MCP providers are unavailable, fall back in this order:

1. Local `docs/**` in the project repository
2. Official upstream documentation
3. Model knowledge (least preferred — state explicitly when used)
