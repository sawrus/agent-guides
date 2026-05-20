#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
TRACE_FILE="${1:?usage: coverage_parse.sh <trace-file>}"
THRESHOLD="${AGENTIC_COVERAGE_THRESHOLD:-90}"
AGENTIC_FILE="$ROOT_DIR/agentic"

python3 - "$AGENTIC_FILE" "$TRACE_FILE" "$THRESHOLD" <<'PY'
import re
import sys
from pathlib import Path

agentic = Path(sys.argv[1]).resolve()
trace = Path(sys.argv[2])
threshold = float(sys.argv[3])

hit = set()
pattern = re.compile(r"^\+(.+?):(\d+):")
for line in trace.read_text(encoding="utf-8", errors="replace").splitlines():
    match = pattern.match(line)
    if not match:
        continue
    path = Path(match.group(1)).resolve()
    if path == agentic:
        hit.add(int(match.group(2)))

covered = len(hit)
total = len(hit)
percent = 100.0 if total else 0.0
print(f"agentic line coverage: {percent:.2f}% ({covered}/{total})")
if percent < threshold:
    raise SystemExit(f"coverage below threshold: {percent:.2f}% < {threshold:.2f}%")
PY
