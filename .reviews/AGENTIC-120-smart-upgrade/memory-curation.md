# Memory Curation Report

## Summary

Reviewed the bounded delivery evidence and upgrade, lifecycle, usage, and Rust architecture documentation. The new upgrade contract has a clear canonical home in `docs/agentic-upgrade/README.md`; memory collection quality could not be assessed.

## Findings

1. **P2 — Clarify historical versus current architecture contracts.** `docs/rust/README.md` describes `main.rs` as returning “exit codes 0/1 only” and lists “same JSON shape” as a manifest parity contract. Current `src/main.rs` propagates `upgrade::ChildExit`, and the new upgrade documentation specifies manifest v2 with generated baselines. These statements can mislead future maintainers reading the rewrite document as current architecture. **Canonical home:** project documentation. **Proposed change:** label the rewrite checklist and original parity requirements as historical, and update current module/interface descriptions or link them to the canonical upgrade contract.

2. **P3 — Reference the upgrade contract rather than duplicating it in memory.** The merge, ownership, rollback, force, and baseline rules are already documented in `docs/agentic-upgrade/README.md`, with links from lifecycle and usage documentation. **Consequence:** copying their full text into memory would introduce another maintenance surface. **Canonical home:** project documentation. **Memory recommendation — store candidate:** only a compact reference to the canonical contract if future sessions repeatedly struggle to retrieve it; no retrieval problem was observed in the supplied evidence.

## MemPalace assessment

MemPalace access was **unavailable**. No query results, writes, or collection duplication evidence were supplied. No claim is made that existing memory is clean or current.

## Limitations and measurements

Documentation findings are based on inspected files and the bounded delivery packet. Live GitHub self-replacement and Windows runtime validation were not performed according to that packet. Token, time, and savings telemetry: **not measured**. Potential retrieval confusion is an inference from inconsistent documentation, not an observed user failure.

## Recommendation

In a separate follow-up, reconcile the historical Rust rewrite document with current interfaces. Keep detailed upgrade behavior in its existing canonical document; defer memory writes until a concrete retrieval benefit is established.
