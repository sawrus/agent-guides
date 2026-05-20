#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
CLI="${AGENTIC_TEST_CLI:-$ROOT_DIR/agentic}"
export AGENTIC_DOCTOR=0
VERSION="$(sed -n 's/^[[:space:]]*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$ROOT_DIR/package.json" | head -n 1)"
TMP_ROOT="$(mktemp -d /tmp/agentic-cli-e2e.XXXXXX)"
trap 'rm -rf "$TMP_ROOT"' EXIT
P="$TMP_ROOT/project"
OUT="$TMP_ROOT/out.log"
VERSION_OUT="$TMP_ROOT/version.log"
"$CLI" --version >"$VERSION_OUT" 2>&1
grep -Fxq "v$VERSION" "$VERSION_OUT"

HOME="$TMP_ROOT/home" AGENTIC_ENABLE_MEMPALACE=n AGENTIC_ENABLE_CONTEXT7=n "$CLI" install \
  --project-dir "$P" --agent-os opencode,codex --areas software --specializations software.backend >"$OUT" 2>&1

grep -Fq "Agentic version: v$VERSION" "$OUT"
grep -Fq 'Skipped MemPalace MCP configuration' "$OUT"
[ ! -d "$P/.mempalace" ]
if [ -f "$P/opencode.json" ]; then
  ! grep -Fq '.mempalace' "$P/opencode.json"
fi
echo 'cli e2e ok'
