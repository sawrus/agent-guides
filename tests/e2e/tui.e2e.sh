#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
CLI="$ROOT_DIR/agentic"
TMP_ROOT="$(mktemp -d /tmp/agentic-tui-e2e.XXXXXX)"
trap 'rm -rf "$TMP_ROOT"' EXIT
OUT="$TMP_ROOT/out.log"
set +e
"$CLI" tui >"$OUT" 2>&1
code=$?
set -e
[ "$code" -eq 1 ]
grep -Fq 'TUI mode requires an interactive terminal' "$OUT"
echo 'tui e2e ok'
