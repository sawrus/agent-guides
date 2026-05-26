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
TEST_HOME="$TMP_ROOT/home"
TEST_XDG_CONFIG_HOME="$TMP_ROOT/xdg-config"
TEST_XDG_DATA_HOME="$TMP_ROOT/xdg-data"
"$CLI" --version >"$VERSION_OUT" 2>&1
grep -Fxq "v$VERSION" "$VERSION_OUT"

HOME="$TEST_HOME" XDG_CONFIG_HOME="$TEST_XDG_CONFIG_HOME" XDG_DATA_HOME="$TEST_XDG_DATA_HOME" AGENTIC_ENABLE_MEMPALACE=n AGENTIC_ENABLE_CONTEXT7=n "$CLI" install \
  --project-dir "$P" --agent-os opencode,codex --areas software --specializations software.backend >"$OUT" 2>&1

grep -Fq "Agentic version: v$VERSION" "$OUT"
grep -Fq 'Skipped MemPalace MCP configuration' "$OUT"
[ ! -d "$P/.mempalace" ]
if [ -f "$P/opencode.json" ]; then
  ! grep -Fq '.mempalace' "$P/opencode.json"
fi

for file in \
  "$ROOT_DIR/agents/instruction_reviewer.md" \
  "$ROOT_DIR/agents/memory_curator.md" \
  "$ROOT_DIR/extensions/opencode/agents/instruction_reviewer.md" \
  "$ROOT_DIR/extensions/opencode/agents/memory_curator.md" \
  "$ROOT_DIR/extensions/claude/agents/instruction_reviewer.md" \
  "$ROOT_DIR/extensions/claude/agents/memory_curator.md" \
  "$ROOT_DIR/extensions/gemini/agents/instruction_reviewer.md" \
  "$ROOT_DIR/extensions/gemini/agents/memory_curator.md" \
  "$ROOT_DIR/extensions/codex/agents/instruction_reviewer.toml" \
  "$ROOT_DIR/extensions/codex/agents/memory_curator.toml" \
  "$P/.opencode/agents/instruction_reviewer.md" \
  "$P/.opencode/agents/memory_curator.md" \
  "$P/.codex/agents/instruction_reviewer.toml" \
  "$P/.codex/agents/memory_curator.toml"; do
  [ -f "$file" ] || { echo "missing expected role file: $file" >&2; exit 1; }
done

grep -Fq "You do NOT review code quality." "$ROOT_DIR/agents/instruction_reviewer.md"
grep -Fq "## Redundant instructions" "$ROOT_DIR/agents/instruction_reviewer.md"
grep -Fq "temporary debugging output" "$ROOT_DIR/agents/memory_curator.md"
grep -Fq "secrets" "$ROOT_DIR/agents/memory_curator.md"
grep -Fq "review_pipeline:" "$ROOT_DIR/docs/review-pipeline.md"
grep -Fq ".reviews/<task-id>/" "$ROOT_DIR/docs/review-pipeline.md"
grep -Fq "instruction-review.md" "$ROOT_DIR/docs/review-pipeline.md"
grep -Fq "instruction_reviewer" "$ROOT_DIR/extensions/opencode/opencode.json"
grep -Fq "memory_curator" "$ROOT_DIR/extensions/opencode/opencode.json"
grep -Fq "# Instruction Effectiveness Review" "$ROOT_DIR/docs/review-pipeline/examples/instruction-review.example.md"
grep -Fq "# Memory Curation Report" "$ROOT_DIR/docs/review-pipeline/examples/memory-curation.example.md"
echo 'cli e2e ok'
