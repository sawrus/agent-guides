#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
CLI="$ROOT_DIR/agentic"
TMP_ROOT="$(mktemp -d /tmp/agentic-cli-e2e.XXXXXX)"
trap 'rm -rf "$TMP_ROOT"' EXIT
P="$TMP_ROOT/project"
OUT="$TMP_ROOT/out.log"
HOME="$TMP_ROOT/home" AGENTIC_ENABLE_MEMPALACE=n AGENTIC_ENABLE_CONTEXT7=n "$CLI" install \
  --project-dir "$P" --agent-os opencode,codex --areas software --specializations software.backend >"$OUT" 2>&1

grep -Fq 'Skipped MemPalace MCP configuration' "$OUT"
[ ! -d "$P/.mempalace" ]
if [ -f "$P/opencode.json" ]; then
  ! grep -Fq '.mempalace' "$P/opencode.json"
fi
echo 'cli e2e ok'
