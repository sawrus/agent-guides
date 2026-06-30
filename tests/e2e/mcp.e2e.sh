#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
CLI="${AGENTIC_TEST_CLI:-$ROOT_DIR/agentic}"
TMP_ROOT="$(mktemp -d /tmp/agentic-mcp-e2e.XXXXXX)"
trap 'rm -rf "$TMP_ROOT"' EXIT

fail() { echo "[mcp-e2e][FAIL] $1" >&2; exit 1; }
assert_exists() { [[ -e "$1" ]] || fail "Expected path to exist: $1"; }
assert_file_contains() { grep -Fq -- "$2" "$1" || fail "Expected '$2' in $1"; }
assert_file_not_contains() { [[ ! -e "$1" ]] && return 0; if grep -Fq -- "$2" "$1"; then fail "Did not expect '$2' in $1"; fi; }

PYTHON_ONLY_BIN="$TMP_ROOT/python-bin"
mkdir -p "$PYTHON_ONLY_BIN"
ln -s "$(command -v python3)" "$PYTHON_ONLY_BIN/python3"
cat > "$PYTHON_ONLY_BIN/pip" <<'EOS'
#!/usr/bin/env bash
exit 0
EOS
cat > "$PYTHON_ONLY_BIN/kubectl" <<'EOS'
#!/usr/bin/env bash
exit 1
EOS
cat > "$PYTHON_ONLY_BIN/docker" <<'EOS'
#!/usr/bin/env bash
exit 1
EOS
chmod +x "$PYTHON_ONLY_BIN/pip" "$PYTHON_ONLY_BIN/kubectl" "$PYTHON_ONLY_BIN/docker"

PROJECT="$TMP_ROOT/project-all"
OUT="$TMP_ROOT/all.log"
HOME="$TMP_ROOT/home-all" PATH="$PYTHON_ONLY_BIN:/usr/bin:/bin" \
AGENTIC_ENABLE_MCPS=opencode-docs,playwright,kubernetes,youtube-transcript,docker-mcp,anydb \
AGENTIC_CONFIRM_DANGEROUS_MCP=1 AGENTIC_DOCTOR=0 \
"$CLI" install \
  --project-dir "$PROJECT" \
  --agent-os opencode,codex,claude,cursor,gemini,kilocode \
  --areas software \
  --specializations software.backend >"$OUT" 2>&1

assert_exists "$PROJECT/opencode.json"
assert_file_contains "$PROJECT/opencode.json" '"$schema": "https://opencode.ai/config.json"'
assert_file_contains "$PROJECT/opencode.json" '"opencode-docs-mcp"'
assert_file_contains "$PROJECT/opencode.json" '"@playwright/mcp@latest"'
assert_file_contains "$PROJECT/opencode.json" '"kubernetes-mcp-server"'
assert_file_contains "$PROJECT/opencode.json" '"@kimtaeyoon83/mcp-server-youtube-transcript"'
assert_file_contains "$PROJECT/opencode.json" '"docker"'
assert_file_contains "$PROJECT/opencode.json" '"anydb-mcp"'
assert_file_contains "$PROJECT/opencode.json" '"mcp"'
assert_file_contains "$PROJECT/opencode.json" '"type": "local"'
assert_file_contains "$PROJECT/opencode.json" '"enabled": true'
assert_file_not_contains "$PROJECT/opencode.json" '"mcpServers"'
assert_file_contains "$PROJECT/.opencode/opencode.json" '"mcp"'
assert_file_not_contains "$PROJECT/.opencode/opencode.json" '"mcpServers"'
assert_file_contains "$PROJECT/.codex/config.toml" '[mcp_servers.opencode]'
assert_file_contains "$PROJECT/.codex/config.toml" '[sandbox_workspace_write]'
assert_file_contains "$PROJECT/.codex/config.toml" 'network_access = true'
assert_file_contains "$PROJECT/.codex/config.toml" 'args = ["-y", "opencode-docs-mcp"]'
assert_file_contains "$PROJECT/.codex/config.toml" 'args = ["-y", "@playwright/mcp@latest"]'
assert_file_contains "$PROJECT/.codex/config.toml" 'startup_timeout_sec = 60'
assert_file_contains "$PROJECT/.codex/config.toml" 'args = ["mcp", "gateway", "run"]'
assert_file_contains "$PROJECT/.codex/config.toml" 'startup_timeout_sec = 30'
assert_file_contains "$PROJECT/.mcp.json" '"playwright"'
assert_file_contains "$PROJECT/.cursor/mcp.json" '"youtube-transcript"'
assert_file_contains "$PROJECT/.gemini/settings.json" '"anydb"'
assert_file_contains "$PROJECT/.kilocode/mcp.json" '"kubernetes"'
assert_file_contains "$PROJECT/.agentic.json" '"opencode-docs"'
assert_file_contains "$PROJECT/.agentic.json" '"docker-mcp"'
assert_file_contains "$OUT" "Kubernetes MCP selected, but 'kubectl version' did not complete successfully."
assert_file_contains "$OUT" "https://kubernetes.io/docs/tasks/tools/"
assert_file_contains "$OUT" "Docker MCP selected, but 'docker mcp --version' did not complete successfully."
assert_file_contains "$OUT" "https://docs.docker.com/get-started/get-docker/"

SKIP_PROJECT="$TMP_ROOT/project-skip-dangerous"
SKIP_OUT="$TMP_ROOT/skip-dangerous.log"
HOME="$TMP_ROOT/home-skip" PATH="$PYTHON_ONLY_BIN:/usr/bin:/bin" \
AGENTIC_ENABLE_MCPS=kubernetes AGENTIC_DOCTOR=0 \
"$CLI" install \
  --project-dir "$SKIP_PROJECT" \
  --agent-os opencode \
  --areas software \
  --specializations software.backend >"$SKIP_OUT" 2>&1
# Dangerous MCPs are now installed without confirmation (confirm dialog removed)
assert_file_contains "$SKIP_PROJECT/opencode.json" 'kubernetes-mcp-server'
assert_file_contains "$SKIP_PROJECT/.agentic.json" '"kubernetes"'

MERGE_PROJECT="$TMP_ROOT/project-merge"
mkdir -p "$MERGE_PROJECT"
cat > "$MERGE_PROJECT/opencode.json" <<'JSON'
{
  "$schema": "https://example.test/custom-schema.json",
  "customField": true,
  "mcpServers": {
    "existing": {
      "command": "keep-me"
    },
    "playwright": {
      "command": "old"
    }
  }
}
JSON
MERGE_OUT="$TMP_ROOT/merge.log"
HOME="$TMP_ROOT/home-merge" PATH="$PYTHON_ONLY_BIN:/usr/bin:/bin" \
AGENTIC_ENABLE_MCPS=playwright AGENTIC_DOCTOR=0 \
"$CLI" install \
  --project-dir "$MERGE_PROJECT" \
  --agent-os opencode \
  --areas software \
  --specializations software.backend >"$MERGE_OUT" 2>&1
assert_file_contains "$MERGE_PROJECT/opencode.json" '"$schema": "https://example.test/custom-schema.json"'
assert_file_contains "$MERGE_PROJECT/opencode.json" '"customField": true'
assert_file_contains "$MERGE_PROJECT/opencode.json" '"existing"'
assert_file_contains "$MERGE_PROJECT/opencode.json" '"keep-me"'
assert_file_contains "$MERGE_PROJECT/opencode.json" '"@playwright/mcp@latest"'
assert_file_not_contains "$MERGE_PROJECT/opencode.json" '"command": "old"'
assert_file_not_contains "$MERGE_PROJECT/opencode.json" '"mcpServers"'
python3 - "$MERGE_PROJECT/opencode.json" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
if "mcpServers" in data:
    raise SystemExit("OpenCode config still contains legacy mcpServers")
mcp = data.get("mcp", {})
if mcp.get("existing", {}).get("command") != ["keep-me"]:
    raise SystemExit("legacy existing server was not migrated to mcp")
if mcp.get("playwright", {}).get("command") != ["npx", "-y", "@playwright/mcp@latest"]:
    raise SystemExit("selected playwright server was not rewritten in mcp")
PY

echo 'mcp e2e ok'
