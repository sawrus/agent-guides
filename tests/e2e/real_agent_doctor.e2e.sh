#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
CLI="${AGENTIC_TEST_CLI:-$ROOT_DIR/agentic}"

TMP_ROOT="$(mktemp -d /tmp/agentic-real-agent-doctor.XXXXXX)"
trap 'rm -rf "$TMP_ROOT"' EXIT

agents=()
for agent in codex opencode claude gemini; do
  if command -v "$agent" >/dev/null 2>&1; then
    agents+=("$agent")
  else
    echo "[real-agent-doctor][FAIL] missing binary: $agent" >&2
    exit 1
  fi
done

if [[ "${#agents[@]}" -eq 0 ]]; then
  echo "[real-agent-doctor][FAIL] no supported real agent binaries installed" >&2
  exit 1
fi

agent_csv="$(IFS=,; printf '%s' "${agents[*]}")"
project="$TMP_ROOT/project"
out="$TMP_ROOT/real-agent-doctor.log"

echo "[real-agent-doctor] running doctor for: $agent_csv"
AGENTIC_ENABLE_CONTEXT7=n \
AGENTIC_ENABLE_MEMPALACE=n \
AGENTIC_DOCTOR=1 \
  "$CLI" install \
    --project-dir "$project" \
    --agent-os "$agent_csv" \
    --areas software \
    --specializations software.backend,software.general >"$out" 2>&1

cat "$out"

if grep -Fq "❌" "$out"; then
  echo "[real-agent-doctor][FAIL] one or more real agent doctor checks failed" >&2
  exit 1
fi

echo "real agent doctor e2e ok"
