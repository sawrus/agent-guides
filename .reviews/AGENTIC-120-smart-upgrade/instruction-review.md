# Instruction Effectiveness Review

## Summary

Reviewed the loaded guidance and bounded evidence for AGENTIC-120-smart-upgrade. Local implementation, documentation, versioning, and required Makefile checks completed; publication, PR creation, and merge were outside the requested delivery.

## Findings

1. **P1 — Completion scope conflicts with generic workflow.**
   Source: `areas/software/general/workflows/development-cycle-workflow.md`, outputs, quality gates, steps 5–6, and Exit; `REVIEW_PIPELINE.md`, activation. The workflow defines completion as a merged PR validated in staging, while this task ends at verified local implementation. The packet also lacks external QA/sign-off. This creates ambiguity about whether post-task review is eligible.
   **Suggested edit:** Add: “Record the requested delivery endpoint during requirements framing. PR, merge, and staging steps apply only when included in that endpoint. Post-task review follows completion and acceptance of that endpoint; distinguish local verification from external sign-off.”

2. **P2 — Toolchain prerequisites are discovered during verification.**
   Source: workflow steps 3–4 and `general-dev-tools` usage. The packet records missing fmt, clippy, and llvm-cov executables, followed by discovery of an existing `/tmp/agentic-review-toolchain` and PATH overrides. This is observed execution friction; its additional cost is not measured.
   **Suggested edit:** Add to technical design: “Before implementation, inspect the required Makefile targets and verify their toolchain prerequisites. Reuse an available compatible toolchain through documented environment overrides; report missing dependencies before starting verification.”

3. **P3 — Root memory description disagrees with the linked protocol.**
   Source: root `AGENTS.md`, MCP Memory Providers; `MEMORY.md`. Root guidance describes “MemPalace session-start queries,” but the protocol says to use MCP context only when it improves accuracy and forbids broad startup searches. The packet reports no available MemPalace tools; no unnecessary memory queries are evidenced. The consequence is instruction ambiguity, not demonstrated wasted calls.
   **Suggested edit:** Replace “MemPalace session-start queries” with “task-scoped MemPalace lookups and durable fact-writing triggers.”

## Limitations and measurements

Evidence consists of the orchestrator’s packet and targeted reads of loaded instructions. No full transcript, external QA/sign-off, live GitHub self-replacement validation, or Windows runtime validation was supplied. Two compile corrections and one clippy correction were reported, but evidence does not establish instruction-related causes.

Token usage, elapsed time, and savings: **not measured**. Context reuse appears supported by the bounded shared packet; efficiency gains cannot be quantified.

## Recommendation

**Minor edits.** Preserve the Makefile validation, safe-path requirements, canonical behavior documentation, version/changelog contract, and advisory read-only review. Clarify delivery completion, check toolchain readiness earlier, and align the root memory summary with its protocol.
