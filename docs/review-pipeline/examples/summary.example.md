# Review Summary

| Specialist | Status | Result |
|---|---|---|
| instruction-reviewer | completed | One scoped guidance replacement proposed. |
| memory-curator | completed | One duplicate-memory update candidate; docs are canonical. |

Evidence covers the supplied guidance, read history, changed docs, and one memory
lookup. No full transcript or memory inventory was inspected. Token/time/savings:
not measured. Neither specialist applied changes.

Priority follow-ups for a separate requested task:
1. Review the exact replacement in [instruction-review.md](instruction-review.example.md).
2. Review the canonical-source proposal in [memory-curation.md](memory-curation.example.md).

If a specialist is unavailable or fails, its row and report placeholder instead
state `unavailable` or `failed` with the reason; completed delivery stays accepted.

## Manual acceptance

Run from the project root:

```bash
make test          # expected: exit code 0, all tests pass
python3 calculator.py "2 + 3 * 4"   # expected output: 14
python3 calculator.py "1 / 0"       # expected: "Error: division by zero", exit code 1
```

Manual check: open `docs/calculator/README.md` and confirm that the usage section
matches the output above. Cleanup: none; the commands do not change files.
