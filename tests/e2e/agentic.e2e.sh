#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
CLI="${AGENTIC_TEST_CLI:-$ROOT_DIR/agentic}"
SOURCE_CLI="$ROOT_DIR/agentic"
export AGENTIC_TEST_SOURCE_AGENTIC="$SOURCE_CLI"
export AGENTIC_DOCTOR=0
TMP_ROOT="$(mktemp -d /tmp/agentic-e2e.XXXXXX)"
TMP_ROOT_REAL="$(cd "$TMP_ROOT" && pwd -P)"
PYTHON_ONLY_BIN="$TMP_ROOT/python-bin"
mkdir -p "$PYTHON_ONLY_BIN"
ln -s "$(command -v python3)" "$PYTHON_ONLY_BIN/python3"
cat > "$PYTHON_ONLY_BIN/pip" <<'EOS'
#!/usr/bin/env bash
exit 0
EOS
chmod +x "$PYTHON_ONLY_BIN/pip"
cleanup() {
  if [[ "${AGENTIC_TEST_KEEP_TMP:-}" == "1" ]]; then
    echo "[e2e] Keeping temp root: $TMP_ROOT" >&2
    return
  fi
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

fail() {
  echo "[e2e][FAIL] $1" >&2
  exit 1
}

assert_exists() {
  local path="$1"
  [[ -e "$path" ]] || fail "Expected path to exist: $path"
}

assert_not_exists() {
  local path="$1"
  [[ ! -e "$path" ]] || fail "Expected path to not exist: $path"
}

assert_executable() {
  local path="$1"
  [[ -x "$path" ]] || fail "Expected executable path: $path"
}

assert_file_contains() {
  local path="$1"
  local needle="$2"
  grep -Fq -- "$needle" "$path" || fail "Expected '$needle' in $path"
}

assert_file_not_contains() {
  local path="$1"
  local needle="$2"
  if grep -Fq -- "$needle" "$path"; then
    fail "Did not expect '$needle' in $path"
  fi
}

assert_output_contains() {
  local output="$1"
  local needle="$2"
  grep -Fq -- "$needle" <<< "$output" || fail "Expected '$needle' in output"
}

assert_output_not_contains() {
  local output="$1"
  local needle="$2"
  if grep -Fq -- "$needle" <<< "$output"; then
    fail "Did not expect '$needle' in output"
  fi
}

changed_paths_report_from_output() {
  local path="$1"
  sed -n 's/^.*Changed paths report: //p' "$path" | tail -1 | tr -d "'"
}

FAKE_GIT_BIN="$TMP_ROOT/fake-git-bin"
mkdir -p "$FAKE_GIT_BIN"
GIT_LOG="$TMP_ROOT/git.log"
cat > "$FAKE_GIT_BIN/git" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
LOG_FILE="${AGENTIC_TEST_GIT_LOG:?missing AGENTIC_TEST_GIT_LOG}"
printf 'git %s\n' "$*" >> "$LOG_FILE"

make_repo() {
  local dest="$1"
  mkdir -p "$dest/areas/software/backend/rules" \
           "$dest/areas/software/backend/skills" \
           "$dest/areas/software/backend/workflows" \
           "$dest/areas/software/backend/prompts" \
           "$dest/areas/software/frontend/rules" \
           "$dest/areas/software/frontend/skills" \
           "$dest/areas/software/frontend/workflows" \
           "$dest/areas/software/frontend/prompts" \
           "$dest/extensions/opencode" \
           "$dest/extensions/codex" \
           "$dest/extensions/claude"
  cat > "$dest/AGENTS.md" <<'EOT'
# Root AGENTS
Dynamic guidance loading
EOT
  cat > "$dest/areas/software/backend/AGENTS.md" <<'EOT'
# Backend AGENTS
backend guidance
EOT
  cat > "$dest/areas/software/frontend/AGENTS.md" <<'EOT'
# Frontend AGENTS
frontend guidance
EOT
  echo 'backend rule' > "$dest/areas/software/backend/rules/backend.md"
  echo 'backend skill' > "$dest/areas/software/backend/skills/backend.md"
  echo 'backend workflow' > "$dest/areas/software/backend/workflows/backend.md"
  echo 'backend prompt' > "$dest/areas/software/backend/prompts/backend.md"
  echo 'frontend rule' > "$dest/areas/software/frontend/rules/frontend.md"
  echo 'frontend skill' > "$dest/areas/software/frontend/skills/frontend.md"
  echo 'frontend workflow' > "$dest/areas/software/frontend/workflows/frontend.md"
  echo 'frontend prompt' > "$dest/areas/software/frontend/prompts/frontend.md"
  echo '{}' > "$dest/extensions/opencode/opencode.json"
  echo '{}' > "$dest/extensions/codex/config.json"
  echo '{}' > "$dest/extensions/claude/config.json"
          cp "${AGENTIC_TEST_SOURCE_AGENTIC:-$SOURCE_CLI}" "$dest/agentic"
}

if [[ "${1:-}" == "clone" ]]; then
  url="${2:?missing clone url}"
  dest="${3:?missing clone dest}"
  mkdir -p "$(dirname -- "$dest")"
  make_repo "$dest"
  exit 0
fi

if [[ "${1:-}" == "-C" ]]; then
  repo_dir="${2:?missing repo dir}"
  shift 2
  if [[ "${1:-}" == "pull" ]] && [[ "${2:-}" == "--ff-only" ]]; then
    echo 'pull complete' > "$repo_dir/.last-pull"
    if [[ -n "${AGENTIC_TEST_PULL_AGENTIC_MARKER:-}" ]]; then
      printf '\n# %s\n' "$AGENTIC_TEST_PULL_AGENTIC_MARKER" >> "$repo_dir/agentic"
    fi
    exit 0
  fi
fi

exit 1
EOS
chmod +x "$FAKE_GIT_BIN/git"

FAKE_PKG_BIN="$TMP_ROOT/fake-pkg-bin"
mkdir -p "$FAKE_PKG_BIN"
cat > "$FAKE_PKG_BIN/brew" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
LOG_FILE="${AGENTIC_TEST_FZF_LOG:?missing AGENTIC_TEST_FZF_LOG}"
printf 'brew %s\n' "$*" >> "$LOG_FILE"

mode="${AGENTIC_TEST_BREW_MODE:-success}"
if [[ "$mode" == "success" ]]; then
  if [[ -n "${AGENTIC_TEST_FZF_BIN_DIR:-}" ]]; then
    mkdir -p "$AGENTIC_TEST_FZF_BIN_DIR"
    cat > "$AGENTIC_TEST_FZF_BIN_DIR/fzf" <<'EOX'
#!/usr/bin/env bash
exit 0
EOX
    chmod +x "$AGENTIC_TEST_FZF_BIN_DIR/fzf"
  fi
  exit 0
fi

exit 1
EOS
chmod +x "$FAKE_PKG_BIN/brew"

echo "[e2e] Scenario 0: no args in non-interactive mode -> usage + exit 1"
OUT0="$TMP_ROOT/no-args-noninteractive.log"
set +e
"$CLI" >"$OUT0" 2>&1
STATUS0=$?
set -e
[[ "$STATUS0" -eq 1 ]] || fail "Expected exit code 1 for no-args non-interactive, got $STATUS0"
assert_file_contains "$OUT0" "Agentic Installer"
assert_file_contains "$OUT0" "Usage:"

echo "[e2e] Scenario 0a: install preflight reports missing Python and pip"
REQ_BIN="$TMP_ROOT/requirements-bin"
mkdir -p "$REQ_BIN"
for tool in bash dirname pwd basename sed head date mktemp; do
  ln -s "$(command -v "$tool")" "$REQ_BIN/$tool"
done

OUT0A="$TMP_ROOT/missing-python.log"
set +e
PATH="$REQ_BIN" HOME="$TMP_ROOT/home-missing-python" "$CLI" install \
  --project-dir "$TMP_ROOT/project-missing-python" \
  --areas software \
  --specializations software.backend >"$OUT0A" 2>&1
STATUS0A=$?
set -e
[[ "$STATUS0A" -eq 1 ]] || fail "Expected exit code 1 for missing python3, got $STATUS0A"
assert_file_contains "$OUT0A" "python3 is required"

cat > "$REQ_BIN/python3" <<'EOS'
#!/usr/bin/env bash
if [[ "${1:-}" == "-m" && "${2:-}" == "pip" ]]; then
  exit 1
fi
exit 0
EOS
chmod +x "$REQ_BIN/python3"
OUT0B="$TMP_ROOT/missing-pip.log"
set +e
PATH="$REQ_BIN" HOME="$TMP_ROOT/home-missing-pip" "$CLI" install \
  --project-dir "$TMP_ROOT/project-missing-pip" \
  --areas software \
  --specializations software.backend >"$OUT0B" 2>&1
STATUS0B=$?
set -e
[[ "$STATUS0B" -eq 1 ]] || fail "Expected exit code 1 for missing pip, got $STATUS0B"
assert_file_contains "$OUT0B" "pip is required to run agentic install/tui"

echo "[e2e] Scenario 1: dev mode install from repository checkout persists --theme=<value> to config"
P1="$TMP_ROOT/project-dev-install"
HOME_DEV_INSTALL="$TMP_ROOT/home-dev-install"
OUT1="$TMP_ROOT/project-dev-install.log"
HOME="$HOME_DEV_INSTALL" "$CLI" install \
  --project-dir "$P1" \
  --agent-os opencode \
  --areas software \
  --specializations software.backend \
  --theme=light >"$OUT1" 2>&1

assert_exists "$P1/.opencode"
assert_exists "$P1/.agent/rules"
assert_exists "$P1/.agent/skills"
assert_exists "$P1/.agent/workflows"
assert_exists "$P1/.agent/prompts"
assert_exists "$P1/AGENTS.md"
assert_exists "$P1/.opencode/AGENTS.md"
assert_file_contains "$P1/.opencode/AGENTS.md" "software/backend"
assert_file_contains "$P1/AGENTS.md" "software/backend"
assert_file_contains "$P1/.opencode/AGENTS.md" "Dynamic guidance loading"
assert_file_contains "$P1/AGENTS.md" "Dynamic guidance loading"
assert_file_contains "$P1/.opencode/AGENTS.md" "generated_by: agentic"
assert_file_contains "$P1/AGENTS.md" "generated_by: agentic"
assert_exists "$P1/.agentic.json"
assert_file_contains "$P1/.agentic.json" "\"managed_files\""
assert_file_contains "$P1/.agentic.json" ".opencode/AGENTS.md"
assert_file_contains "$P1/.agentic.json" "\"AGENTS.md\""
assert_file_contains "$P1/.agentic.json" "https://github.com/sawrus/agent-guides"
assert_file_not_contains "$P1/.opencode/opencode.json" "\"context7\""
assert_file_contains "$P1/.opencode/plugins/telegram-notification.ts" "Generated by agentic"
assert_exists "$HOME_DEV_INSTALL/.config/agentic/opencode-plugins.json"
assert_file_contains "$HOME_DEV_INSTALL/.config/agentic/opencode-plugins.json" "\"enabled\": false"
assert_exists "$HOME_DEV_INSTALL/.config/agentic/config"
assert_file_contains "$HOME_DEV_INSTALL/.config/agentic/config" "theme=light"
assert_file_contains "$OUT1" "Created directories:"
assert_file_contains "$OUT1" "Copied/generated paths:"
assert_file_contains "$OUT1" "Changed paths report:"
assert_file_not_contains "$OUT1" "$P1/.opencode/AGENTS.md"
assert_file_not_contains "$OUT1" "$P1/.agent/rules/architecture.md"
assert_file_not_contains "$OUT1" "Copy extension"
assert_file_not_contains "$OUT1" "Copy software.backend/"
assert_file_not_contains "$OUT1" "Skip software.backend/"
REPORT1="$(changed_paths_report_from_output "$OUT1")"
assert_exists "$REPORT1"
assert_file_contains "$REPORT1" "Created directories ("
assert_file_contains "$REPORT1" "Copied/generated paths ("
assert_file_contains "$REPORT1" "$P1/.opencode/AGENTS.md"
assert_file_contains "$REPORT1" "$P1/.agent/rules/architecture.md"

echo "[e2e] Scenario 1ab: MemPalace runtime check passes when mempalace-mcp is available"
P1_MEM_OK="$TMP_ROOT/project-mempalace-ok"
HOME_MEM_OK="$TMP_ROOT/home-mempalace-ok"
OUT1AB_OK="$TMP_ROOT/project-mempalace-ok.log"
FAKE_MEMPALACE_BIN="$TMP_ROOT/fake-mempalace-bin"
FAKE_MEMPALACE_PIP_LOG="$TMP_ROOT/fake-mempalace-pip.log"
mkdir -p "$FAKE_MEMPALACE_BIN"
cat > "$FAKE_MEMPALACE_BIN/pip" <<'EOS'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${FAKE_MEMPALACE_PIP_LOG:?missing FAKE_MEMPALACE_PIP_LOG}"
exit 0
EOS
cat > "$FAKE_MEMPALACE_BIN/mempalace-mcp" <<'EOS'
#!/usr/bin/env bash
exit 0
EOS
cat > "$FAKE_MEMPALACE_BIN/mempalace" <<'EOS'
#!/usr/bin/env bash
exit 0
EOS
chmod +x "$FAKE_MEMPALACE_BIN"/*

env HOME="$HOME_MEM_OK" PATH="$FAKE_MEMPALACE_BIN:$PYTHON_ONLY_BIN:/usr/bin:/bin" FAKE_MEMPALACE_PIP_LOG="$FAKE_MEMPALACE_PIP_LOG" AGENTIC_ENABLE_MEMPALACE=y "$CLI" install \
  --project-dir "$P1_MEM_OK" \
  --agent-os codex \
  --areas software \
  --specializations software.backend \
  --theme=light >"$OUT1AB_OK" 2>&1
assert_file_contains "$FAKE_MEMPALACE_PIP_LOG" "install mempalace"
assert_file_contains "$OUT1AB_OK" "MemPalace package installed via 'pip install mempalace'"
assert_file_contains "$OUT1AB_OK" "MemPalace MCP binary found: mempalace-mcp"
assert_file_contains "$P1_MEM_OK/.codex/config.toml" "[features]"
assert_file_contains "$P1_MEM_OK/.codex/config.toml" "memories = true"
assert_file_contains "$P1_MEM_OK/.codex/config.toml" "[mcp_servers.mempalace]"
assert_file_contains "$OUT1AB_OK" "Initializing project memory"
assert_file_contains "$P1_MEM_OK/.mempalaceignore" "node_modules/"
assert_file_contains "$P1_MEM_OK/.mempalaceignore" "*.parquet"
assert_file_contains "$P1_MEM_OK/.mempalaceignore" ".git/"
assert_file_contains "$P1_MEM_OK/.agentic.json" ".mempalaceignore"

echo "[e2e] Scenario 1ab0: MemPalace project wing uses real basename for dot project dir"
P1_MEM_DOT="$TMP_ROOT/proxy-api"
HOME_MEM_DOT="$TMP_ROOT/home-mempalace-dot"
OUT1AB_DOT="$TMP_ROOT/project-mempalace-dot.log"
FAKE_MEMPALACE_DOT_BIN="$TMP_ROOT/fake-mempalace-dot-bin"
FAKE_MEMPALACE_DOT_LOG="$TMP_ROOT/fake-mempalace-dot.log"
mkdir -p "$P1_MEM_DOT" "$FAKE_MEMPALACE_DOT_BIN"
P1_MEM_DOT_REAL="$(cd "$P1_MEM_DOT" && pwd -P)"
cat > "$FAKE_MEMPALACE_DOT_BIN/pip" <<'EOS'
#!/usr/bin/env bash
exit 0
EOS
cat > "$FAKE_MEMPALACE_DOT_BIN/mempalace-mcp" <<'EOS'
#!/usr/bin/env bash
exit 0
EOS
cat > "$FAKE_MEMPALACE_DOT_BIN/mempalace" <<'EOS'
#!/usr/bin/env bash
printf 'mempalace %s\n' "$*" >> "${FAKE_MEMPALACE_DOT_LOG:?missing FAKE_MEMPALACE_DOT_LOG}"
exit 0
EOS
chmod +x "$FAKE_MEMPALACE_DOT_BIN"/*

(
  cd "$P1_MEM_DOT"
  env HOME="$HOME_MEM_DOT" PATH="$FAKE_MEMPALACE_DOT_BIN:$PYTHON_ONLY_BIN:/usr/bin:/bin" FAKE_MEMPALACE_DOT_LOG="$FAKE_MEMPALACE_DOT_LOG" AGENTIC_ENABLE_MEMPALACE=y "$CLI" install \
    --project-dir . \
    --agent-os codex \
    --areas software \
    --specializations software.backend \
    --theme=light >"$OUT1AB_DOT" 2>&1
)
assert_file_contains "$OUT1AB_DOT" "Initializing project memory at $P1_MEM_DOT_REAL (wing: proxy_api)"
assert_file_contains "$OUT1AB_DOT" "Project dir: $P1_MEM_DOT_REAL"
assert_file_contains "$FAKE_MEMPALACE_DOT_LOG" "mempalace mine $P1_MEM_DOT_REAL --wing proxy_api"

echo "[e2e] Scenario 1ab1: MemPalace pip install failure reports log path and reason"
P1_MEM_PIP_FAIL="$TMP_ROOT/project-mempalace-pip-fail"
HOME_MEM_PIP_FAIL="$TMP_ROOT/home-mempalace-pip-fail"
OUT1AB_PIP_FAIL="$TMP_ROOT/project-mempalace-pip-fail.log"
FAKE_MEMPALACE_PIP_FAIL_BIN="$TMP_ROOT/fake-mempalace-pip-fail-bin"
mkdir -p "$FAKE_MEMPALACE_PIP_FAIL_BIN"
cat > "$FAKE_MEMPALACE_PIP_FAIL_BIN/pip" <<'EOS'
#!/usr/bin/env bash
printf '%s\n' "error: network unavailable" >&2
printf '%s\n' "pip could not reach package index" >&2
exit 23
EOS
chmod +x "$FAKE_MEMPALACE_PIP_FAIL_BIN/pip"
env HOME="$HOME_MEM_PIP_FAIL" PATH="$FAKE_MEMPALACE_PIP_FAIL_BIN:$PYTHON_ONLY_BIN:/usr/bin:/bin" AGENTIC_ENABLE_MEMPALACE=y "$CLI" install \
  --project-dir "$P1_MEM_PIP_FAIL" \
  --agent-os codex \
  --areas software \
  --specializations software.backend \
  --theme=light >"$OUT1AB_PIP_FAIL" 2>&1
assert_file_contains "$OUT1AB_PIP_FAIL" "Unable to auto-install mempalace via pip; continuing with manual setup instructions (exit 23, log:"
assert_file_contains "$OUT1AB_PIP_FAIL" "pip failure reason: error: network unavailable"
PIP_FAIL_LOG="$(sed -n 's/^.*Unable to auto-install mempalace via pip; continuing with manual setup instructions (exit 23, log: \(.*\))$/\1/p' "$OUT1AB_PIP_FAIL" | tail -1)"
[[ -n "$PIP_FAIL_LOG" ]] || fail "Expected MemPalace pip failure log path in $OUT1AB_PIP_FAIL"
assert_file_contains "$PIP_FAIL_LOG" "pip could not reach package index"
RUN_FAIL_LOG="$(sed -n 's/^.*Agentic log file: //p' "$OUT1AB_PIP_FAIL" | tail -1 | tr -d "'")"
[[ -n "$RUN_FAIL_LOG" ]] || fail "Expected Agentic run log path in $OUT1AB_PIP_FAIL"
assert_file_contains "$RUN_FAIL_LOG" "--- MemPalace pip install output begin ---"
assert_file_contains "$RUN_FAIL_LOG" "pip could not reach package index"
assert_file_contains "$P1_MEM_PIP_FAIL/.codex/config.toml" "[features]"
assert_file_contains "$P1_MEM_PIP_FAIL/.codex/config.toml" "memories = true"
assert_file_contains "$P1_MEM_PIP_FAIL/.codex/config.toml" "[mcp_servers.mempalace]"

echo "[e2e] Scenario 1ab2: OpenCode MemPalace init logs failures with architecture warning"
P1_MEM_OC="$TMP_ROOT/project-mempalace-opencode"
P1_MEM_OC_REAL="$TMP_ROOT_REAL/project-mempalace-opencode"
HOME_MEM_OC="$TMP_ROOT/home-mempalace-opencode"
OUT1AB_OC="$TMP_ROOT/project-mempalace-opencode.log"
FAKE_MEMPALACE_OC_BIN="$TMP_ROOT/fake-mempalace-opencode-bin"
FAKE_MEMPALACE_OC_LOG="$TMP_ROOT/fake-mempalace-opencode.log"
mkdir -p "$FAKE_MEMPALACE_OC_BIN"
cat > "$FAKE_MEMPALACE_OC_BIN/pip" <<'EOS'
#!/usr/bin/env bash
exit 0
EOS
cat > "$FAKE_MEMPALACE_OC_BIN/mempalace-mcp" <<'EOS'
#!/usr/bin/env bash
exit 0
EOS
cat > "$FAKE_MEMPALACE_OC_BIN/mempalace" <<'EOS'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${FAKE_MEMPALACE_OC_LOG:?missing FAKE_MEMPALACE_OC_LOG}"
if [[ "${1:-}" == "init" ]]; then
  printf '%s\n' "fake init stderr" >&2
  printf '%s\n' "ImportError: numpy incompatible architecture" >&2
  exit 7
fi
if [[ "${1:-}" == "mine" ]]; then
  exit 9
fi
exit 0
EOS
chmod +x "$FAKE_MEMPALACE_OC_BIN"/*
env HOME="$HOME_MEM_OC" PATH="$FAKE_MEMPALACE_OC_BIN:$PYTHON_ONLY_BIN:/usr/bin:/bin" FAKE_MEMPALACE_OC_LOG="$FAKE_MEMPALACE_OC_LOG" AGENTIC_ENABLE_MEMPALACE=y "$CLI" install \
  --project-dir "$P1_MEM_OC" \
  --agent-os opencode \
  --areas software \
  --specializations software.backend \
  --theme=light >"$OUT1AB_OC" 2>&1
# mempalace init IS now attempted (always for all agent IDEs)
assert_exists "$FAKE_MEMPALACE_OC_LOG"
assert_file_contains "$FAKE_MEMPALACE_OC_LOG" "init $P1_MEM_OC_REAL --yes --no-llm"
# Init fails → architecture warning is shown
assert_file_contains "$OUT1AB_OC" "Python/NumPy architecture is inconsistent"
# Fallback instructions shown after failure
assert_file_contains "$OUT1AB_OC" "Optional MemPalace project indexing instructions for target project: $P1_MEM_OC_REAL"
# Config files still written despite init failure
assert_file_contains "$P1_MEM_OC/.opencode/opencode.json" "mempalace-mcp"
assert_file_contains "$P1_MEM_OC/.mempalaceignore" "node_modules/"
assert_file_contains "$P1_MEM_OC/.agentic.json" ".mempalaceignore"

echo "[e2e] Scenario 1ac: MemPalace runtime check warns and install continues when module is unavailable"
P1_MEM_WARN="$TMP_ROOT/project-mempalace-warn"
HOME_MEM_WARN="$TMP_ROOT/home-mempalace-warn"
OUT1AB_WARN="$TMP_ROOT/project-mempalace-warn.log"
env HOME="$HOME_MEM_WARN" PATH="$PYTHON_ONLY_BIN:/usr/bin:/bin" AGENTIC_ENABLE_MEMPALACE=y "$CLI" install \
  --project-dir "$P1_MEM_WARN" \
  --agent-os codex \
  --areas software \
  --specializations software.backend \
  --theme=light >"$OUT1AB_WARN" 2>&1
assert_file_contains "$OUT1AB_WARN" "mempalace-mcp is unavailable; install/repair MemPalace and re-run setup"
assert_file_contains "$P1_MEM_WARN/.codex/config.toml" "[features]"
assert_file_contains "$P1_MEM_WARN/.codex/config.toml" "memories = true"
assert_file_contains "$P1_MEM_WARN/.codex/config.toml" "[mcp_servers.mempalace]"
assert_file_contains "$OUT1AB_WARN" "Optional MemPalace project indexing instructions for target project:"

echo "[e2e] Scenario 1a: multi-target opencode,codex writes OpenCode and root AGENTS.md"
P1_MULTI="$TMP_ROOT/project-multi-target"
HOME_MULTI="$TMP_ROOT/home-multi-target"
HOME="$HOME_MULTI" "$CLI" install \
  --project-dir "$P1_MULTI" \
  --agent-os opencode,codex \
  --areas software \
  --specializations software.backend \
  --theme=light

assert_exists "$P1_MULTI/.opencode/AGENTS.md"
assert_exists "$P1_MULTI/AGENTS.md"
assert_file_contains "$P1_MULTI/.opencode/AGENTS.md" "software/backend"
assert_file_contains "$P1_MULTI/AGENTS.md" "software/backend"
assert_file_contains "$P1_MULTI/.agentic.json" ".opencode/AGENTS.md"
assert_file_contains "$P1_MULTI/.agentic.json" "\"AGENTS.md\""

echo "[e2e] Scenario 1aa: install prints missing binary recommendations for selected gemini and antigravity"
P1_BIN="$TMP_ROOT/project-binary-recommendations"
HOME_BIN="$TMP_ROOT/home-binary-recommendations"
OUT1AA="$TMP_ROOT/project-binary-recommendations.log"
env HOME="$HOME_BIN" PATH="$PYTHON_ONLY_BIN:/usr/bin:/bin" "$CLI" install \
  --project-dir "$P1_BIN" \
  --agent-os gemini,antigravity \
  --areas software \
  --specializations software.backend \
  --theme=light >"$OUT1AA" 2>&1
assert_file_contains "$OUT1AA" "=== Agent binary setup recommendations ==="
assert_file_contains "$OUT1AA" "- gemini: binary 'gemini' is not installed"
assert_file_contains "$OUT1AA" "https://github.com/google-gemini/gemini-cli"
assert_file_contains "$OUT1AA" "- antigravity: binary 'antigravity' is not installed"
assert_file_contains "$OUT1AA" "https://github.com/getantigravity/antigravity"

echo "[e2e] Scenario 1b: interactive install asks before enabling Context7"
P1_CTX="$TMP_ROOT/project-context7"
HOME_CTX="$TMP_ROOT/home-context7"
OUT1A="$TMP_ROOT/project-context7.log"
printf '%s\n' "y" "2" "" | \
  env HOME="$HOME_CTX" PATH="$PYTHON_ONLY_BIN:/usr/bin:/bin" AGENTIC_FORCE_INTERACTIVE=1 CONTEXT7_API_KEY="test-context7-key" "$CLI" install \
    --project-dir "$P1_CTX" \
    --agent-os codex \
    --areas software \
    --specializations software.backend \
    --theme=light >"$OUT1A" 2>&1
assert_file_contains "$P1_CTX/.codex/config.toml" "[features]"
assert_file_contains "$P1_CTX/.codex/config.toml" "memories = true"
assert_file_contains "$P1_CTX/.codex/config.toml" "[mcp_servers.context7]"
assert_file_contains "$P1_CTX/.codex/config.toml" "test-context7-key"
assert_file_contains "$OUT1A" "Context7 API key mode:"

P1_CTX_EMPTY="$TMP_ROOT/project-context7-empty-key"
OUT1A_EMPTY="$TMP_ROOT/project-context7-empty-key.log"
printf '%s\n' "y" "1" | \
  env HOME="$HOME_CTX" PATH="$PYTHON_ONLY_BIN:/usr/bin:/bin" AGENTIC_FORCE_INTERACTIVE=1 "$CLI" install \
    --project-dir "$P1_CTX_EMPTY" \
    --agent-os codex \
    --areas software \
    --specializations software.backend \
    --theme=light >"$OUT1A_EMPTY" 2>&1
assert_file_contains "$P1_CTX_EMPTY/.codex/config.toml" "[features]"
assert_file_contains "$P1_CTX_EMPTY/.codex/config.toml" "memories = true"
assert_file_contains "$P1_CTX_EMPTY/.codex/config.toml" "[mcp_servers.context7]"
assert_file_not_contains "$P1_CTX_EMPTY/.codex/config.toml" "CONTEXT7_API_KEY"
assert_file_contains "$OUT1A_EMPTY" "Context7 MCP configured without an API key."
assert_file_contains "$OUT1A_EMPTY" "Context7 API key mode:"
assert_file_not_contains "$OUT1A_EMPTY" "To add a Context7 API key later"
assert_file_not_contains "$OUT1A_EMPTY" "ctx7_your_api_key_here"

echo "[e2e] Scenario 1b1: Context7 writes antigravity-specific path"
P1_CTX_MULTI="$TMP_ROOT/project-context7-antigravity"
OUT1A_MULTI="$TMP_ROOT/project-context7-antigravity.log"
printf '%s\n' "y" "1" | \
  env HOME="$HOME_CTX" PATH="$PYTHON_ONLY_BIN:/usr/bin:/bin" AGENTIC_FORCE_INTERACTIVE=1 "$CLI" install \
    --project-dir "$P1_CTX_MULTI" \
    --agent-os antigravity \
    --areas software \
    --specializations software.backend \
    --theme=light >"$OUT1A_MULTI" 2>&1
assert_file_contains "$HOME_CTX/.gemini/antigravity/mcp_config.json" "\"context7\""
assert_file_contains "$OUT1A_MULTI" "$HOME_CTX/.gemini/antigravity/mcp_config.json"
assert_not_exists "$P1_CTX_MULTI/.antigravity/mcp.json"
assert_not_exists "$P1_CTX_MULTI/.kilocode/mcp.json"

echo "[e2e] Scenario 1b2: non-interactive Context7 enablement via AGENTIC_ENABLE_CONTEXT7"
P1_CTX_ENV="$TMP_ROOT/project-context7-env"
OUT1A_ENV="$TMP_ROOT/project-context7-env.log"
env HOME="$HOME_CTX" AGENTIC_ENABLE_CONTEXT7=y CONTEXT7_API_KEY=env-context7-key "$CLI" install \
  --project-dir "$P1_CTX_ENV" \
  --agent-os codex \
  --areas software \
  --specializations software.backend \
  --theme=light >"$OUT1A_ENV" 2>&1
assert_file_contains "$P1_CTX_ENV/.codex/config.toml" "[features]"
assert_file_contains "$P1_CTX_ENV/.codex/config.toml" "memories = true"
assert_file_contains "$P1_CTX_ENV/.codex/config.toml" "[mcp_servers.context7]"
assert_file_contains "$P1_CTX_ENV/.codex/config.toml" "env-context7-key"

echo "[e2e] Scenario 1b3: interactive OpenCode plugin multi-select enables agent-model-mapper only"
P1_OC_PLUGINS="$TMP_ROOT/project-opencode-plugins"
HOME_OC_PLUGINS="$TMP_ROOT/home-opencode-plugins"
OUT1A_OC_PLUGINS="$TMP_ROOT/project-opencode-plugins.log"
printf '%s\n' "n" "2" "1" "2" "1" "2" "1" "2" "1" "2" "1" "2" "1" "2" "1" "2" "1" "2" "1" "2" "y" "n" "n" | \
  env HOME="$HOME_OC_PLUGINS" AGENTIC_FORCE_INTERACTIVE=1 AGENTIC_OPENCODE_PROFILE=none AGENTIC_AGENT_MODEL_MAPPER_NO_FZF=1 PATH="$FAKE_GIT_BIN:$PYTHON_ONLY_BIN:/usr/bin:/bin" "$CLI" install \
    --project-dir "$P1_OC_PLUGINS" \
    --agent-os opencode \
    --areas software \
    --specializations software.backend \
    --theme=light >"$OUT1A_OC_PLUGINS" 2>&1
assert_exists "$HOME_OC_PLUGINS/.config/agentic/opencode-plugins.json"
assert_file_contains "$HOME_OC_PLUGINS/.config/agentic/opencode-plugins.json" "\"enabled\": true"
assert_file_contains "$HOME_OC_PLUGINS/.config/agentic/opencode-plugins.json" "\"agentModelMapper\""
assert_file_contains "$HOME_OC_PLUGINS/.config/agentic/opencode-plugins.json" "\"telegram\""
assert_file_not_contains "$HOME_OC_PLUGINS/.config/agentic/opencode-plugins.json" "botToken"
assert_file_not_contains "$HOME_OC_PLUGINS/.config/agentic/opencode-plugins.json" "chatId"
assert_file_not_contains "$OUT1A_OC_PLUGINS" "Telegram bot token (empty disables plugin):"
assert_file_contains "$OUT1A_OC_PLUGINS" "agent-model-mapper: updated .opencode/opencode.json"
assert_exists "$P1_OC_PLUGINS/.opencode/agent-model-mapper.state.json"
assert_not_exists "$P1_OC_PLUGINS/.opencode/plugins/agent-model-mapper.ts"
assert_file_contains "$P1_OC_PLUGINS/.agentic.json" '"opencode_plugins"'
assert_file_contains "$P1_OC_PLUGINS/.agentic.json" '"agentModelMapper"'

echo "[e2e] Scenario 1b3b: interactive OpenCode telegram plugin stores credentials in project manifest"
P1_OC_TELEGRAM="$TMP_ROOT/project-opencode-telegram"
HOME_OC_TELEGRAM="$TMP_ROOT/home-opencode-telegram"
OUT1A_OC_TELEGRAM="$TMP_ROOT/project-opencode-telegram.log"
TELEGRAM_TOKEN="123456:test-token"
TELEGRAM_CHAT="987654321"
printf '%s\n' "n" "1" "$TELEGRAM_TOKEN" "$TELEGRAM_CHAT" "n" "n" | \
  env HOME="$HOME_OC_TELEGRAM" AGENTIC_FORCE_INTERACTIVE=1 AGENTIC_OPENCODE_PROFILE=none AGENTIC_DOCTOR=0 PATH="$FAKE_GIT_BIN:$PYTHON_ONLY_BIN:/usr/bin:/bin" "$CLI" install \
    --project-dir "$P1_OC_TELEGRAM" \
    --agent-os opencode \
    --areas software \
    --specializations software.backend \
    --theme=light >"$OUT1A_OC_TELEGRAM" 2>&1
assert_file_contains "$P1_OC_TELEGRAM/.agentic.json" '"botToken": "123456:test-token"'
assert_file_contains "$P1_OC_TELEGRAM/.agentic.json" '"chatId": "987654321"'
assert_file_not_contains "$HOME_OC_TELEGRAM/.config/agentic/opencode-plugins.json" "$TELEGRAM_TOKEN"
assert_file_not_contains "$HOME_OC_TELEGRAM/.config/agentic/opencode-plugins.json" "$TELEGRAM_CHAT"
if [[ -z "${AGENTIC_COVERAGE_TRACE_FILE:-}" ]]; then
  assert_file_not_contains "$OUT1A_OC_TELEGRAM" "$TELEGRAM_TOKEN"
  assert_file_not_contains "$OUT1A_OC_TELEGRAM" "$TELEGRAM_CHAT"
fi

echo "[e2e] Scenario 1b4: interactive OpenCode plugin multi-select with no selection does not request Telegram credentials"
P1_OC_NO_PLUGINS="$TMP_ROOT/project-opencode-no-plugins"
HOME_OC_NO_PLUGINS="$TMP_ROOT/home-opencode-no-plugins"
OUT1A_OC_NO_PLUGINS="$TMP_ROOT/project-opencode-no-plugins.log"
printf '%s\n' "n" "" "n" "n" | \
  env HOME="$HOME_OC_NO_PLUGINS" AGENTIC_FORCE_INTERACTIVE=1 AGENTIC_OPENCODE_PROFILE=none PATH="$FAKE_GIT_BIN:$PYTHON_ONLY_BIN:/usr/bin:/bin" "$CLI" install \
    --project-dir "$P1_OC_NO_PLUGINS" \
    --agent-os opencode \
    --areas software \
    --specializations software.backend \
    --theme=light >"$OUT1A_OC_NO_PLUGINS" 2>&1
assert_exists "$HOME_OC_NO_PLUGINS/.config/agentic/opencode-plugins.json"
assert_file_contains "$HOME_OC_NO_PLUGINS/.config/agentic/opencode-plugins.json" "\"telegram\""
assert_file_contains "$HOME_OC_NO_PLUGINS/.config/agentic/opencode-plugins.json" "\"enabled\": false"
assert_file_contains "$HOME_OC_NO_PLUGINS/.config/agentic/opencode-plugins.json" "\"agentModelMapper\""
assert_file_not_contains "$OUT1A_OC_NO_PLUGINS" "Telegram bot token (empty disables plugin):"
assert_not_exists "$P1_OC_NO_PLUGINS/.opencode/plugins/model-checker.ts"
assert_not_exists "$P1_OC_NO_PLUGINS/.opencode/plugins/model-checker.json"
assert_not_exists "$P1_OC_NO_PLUGINS/.opencode/plugins/agent-model-mapper.ts"
assert_file_not_contains "$P1_OC_NO_PLUGINS/.opencode/opencode.json" "agent-model-mapper"
assert_file_not_contains "$P1_OC_NO_PLUGINS/.opencode/opencode.json" "model-checker"

echo "[e2e] Scenario 1c: rerun skips user-modified managed files"
P1_RULE="$P1/.agent/rules/architecture.md"
assert_exists "$P1_RULE"
printf '%s\n' "# user edit" >> "$P1_RULE"
OUT1B="$TMP_ROOT/project-dev-rerun.log"
HOME="$HOME_DEV_INSTALL" "$CLI" install \
  --project-dir "$P1" \
  --agent-os opencode \
  --areas software \
  --specializations software.backend \
  --theme=light >"$OUT1B" 2>&1
assert_file_contains "$P1_RULE" "# user edit"
assert_file_contains "$OUT1B" "Skipping user-modified managed file: .agent/rules/architecture.md"
assert_file_contains "$P1/.agentic.json" ".agent/rules/architecture.md"

echo "[e2e] Scenario 2: self-install creates agentic binary"
HOME_SELF="$TMP_ROOT/home-self"
BIN_DIR="$HOME_SELF/.local/bin"
OUT2A="$TMP_ROOT/self-install-dry.log"
OUT2B="$TMP_ROOT/self-install-real.log"

HOME="$HOME_SELF" "$CLI" self-install --bin-dir "$BIN_DIR" --dry-run >"$OUT2A" 2>&1
assert_not_exists "$BIN_DIR/agentic"
assert_file_contains "$OUT2A" "Target binary: $BIN_DIR/agentic"
assert_file_contains "$OUT2A" "Config directory: $HOME_SELF/.config/agentic"
assert_file_contains "$OUT2A" "Knowledge base repo: $HOME_SELF/.local/share/agentic/repo"

HOME="$HOME_SELF" "$CLI" self-install --bin-dir "$BIN_DIR" >"$OUT2B" 2>&1
assert_exists "$BIN_DIR/agentic"
assert_executable "$BIN_DIR/agentic"
assert_not_exists "$BIN_DIR/agentos-install"
assert_file_contains "$OUT2B" "Install fzf requested: false"

echo "[e2e] Scenario 2a: self-install --force from installed binary does not copy file onto itself"
OUT2AA="$TMP_ROOT/self-install-force-same-target.log"
HOME="$HOME_SELF" "$BIN_DIR/agentic" self-install --bin-dir "$BIN_DIR" --force >"$OUT2AA" 2>&1
assert_file_contains "$OUT2AA" "Source and target are already the same file: $BIN_DIR/agentic"
assert_file_contains "$OUT2AA" "Nothing to copy."

echo "[e2e] Scenario 2b: self-install does not install fzf without --install-fzf"
HOME_SELF_NO_FZF_FLAG="$TMP_ROOT/home-self-no-fzf-flag"
BIN_DIR_NO_FZF_FLAG="$HOME_SELF_NO_FZF_FLAG/.local/bin"
NO_FZF_PATH_SELF="$TMP_ROOT/no-fzf-self-install"
OUT2C="$TMP_ROOT/self-install-no-fzf-flag.log"
FZF_LOG_NO_FLAG="$TMP_ROOT/fzf-no-flag.log"
mkdir -p "$NO_FZF_PATH_SELF"

HOME="$HOME_SELF_NO_FZF_FLAG" \
  PATH="$FAKE_PKG_BIN:$NO_FZF_PATH_SELF:/usr/bin:/bin" \
  AGENTIC_PLATFORM_OVERRIDE=macos \
  AGENTIC_TEST_FZF_LOG="$FZF_LOG_NO_FLAG" \
  AGENTIC_TEST_BREW_MODE=success \
  AGENTIC_TEST_FZF_BIN_DIR="$NO_FZF_PATH_SELF" \
  "$CLI" self-install --bin-dir "$BIN_DIR_NO_FZF_FLAG" >"$OUT2C" 2>&1

assert_exists "$BIN_DIR_NO_FZF_FLAG/agentic"
assert_not_exists "$NO_FZF_PATH_SELF/fzf"
assert_not_exists "$FZF_LOG_NO_FLAG"
assert_file_contains "$OUT2C" "Install fzf requested: false"

echo "[e2e] Scenario 2c: self-install --install-fzf installs fzf when requested"
HOME_SELF_WITH_FZF="$TMP_ROOT/home-self-with-fzf"
BIN_DIR_WITH_FZF="$HOME_SELF_WITH_FZF/.local/bin"
FZF_PATH_SELF="$TMP_ROOT/fzf-self-install"
OUT2D="$TMP_ROOT/self-install-with-fzf.log"
FZF_LOG_WITH_FLAG="$TMP_ROOT/fzf-with-flag.log"
mkdir -p "$FZF_PATH_SELF"

HOME="$HOME_SELF_WITH_FZF" \
  PATH="$FAKE_PKG_BIN:$FZF_PATH_SELF:/usr/bin:/bin" \
  AGENTIC_PLATFORM_OVERRIDE=macos \
  AGENTIC_TEST_FZF_LOG="$FZF_LOG_WITH_FLAG" \
  AGENTIC_TEST_BREW_MODE=success \
  AGENTIC_TEST_FZF_BIN_DIR="$FZF_PATH_SELF" \
  "$CLI" self-install --bin-dir "$BIN_DIR_WITH_FZF" --install-fzf >"$OUT2D" 2>&1

assert_exists "$BIN_DIR_WITH_FZF/agentic"
assert_exists "$FZF_PATH_SELF/fzf"
assert_file_contains "$FZF_LOG_WITH_FLAG" "brew install fzf"
assert_file_contains "$OUT2D" "Install fzf requested: true"

echo "[e2e] Scenario 2d: self-install --install-fzf falls back on install failure"
HOME_SELF_WITH_FZF_FAIL="$TMP_ROOT/home-self-with-fzf-fail"
BIN_DIR_WITH_FZF_FAIL="$HOME_SELF_WITH_FZF_FAIL/.local/bin"
FZF_PATH_SELF_FAIL="$TMP_ROOT/fzf-self-install-fail"
OUT2E="$TMP_ROOT/self-install-with-fzf-fail.log"
FZF_LOG_WITH_FLAG_FAIL="$TMP_ROOT/fzf-with-flag-fail.log"
mkdir -p "$FZF_PATH_SELF_FAIL"

HOME="$HOME_SELF_WITH_FZF_FAIL" \
  PATH="$FAKE_PKG_BIN:$FZF_PATH_SELF_FAIL:/usr/bin:/bin" \
  AGENTIC_PLATFORM_OVERRIDE=macos \
  AGENTIC_TEST_FZF_LOG="$FZF_LOG_WITH_FLAG_FAIL" \
  AGENTIC_TEST_BREW_MODE=fail \
  AGENTIC_TEST_FZF_BIN_DIR="$FZF_PATH_SELF_FAIL" \
  "$CLI" self-install --bin-dir "$BIN_DIR_WITH_FZF_FAIL" --install-fzf >"$OUT2E" 2>&1

assert_exists "$BIN_DIR_WITH_FZF_FAIL/agentic"
assert_file_contains "$FZF_LOG_WITH_FLAG_FAIL" "brew install fzf"
assert_file_contains "$OUT2E" "Could not auto-install fzf. TUI will use index-based fallback menus."

echo "[e2e] Scenario 3: installed mode bootstrap clone on first command"
HOME_INSTALLED="$TMP_ROOT/home-installed"
INSTALLED_BIN="$HOME_SELF/.local/bin/agentic"
OUT3="$TMP_ROOT/installed-list.log"
LIST_OUTPUT="$({ HOME="$HOME_INSTALLED" PATH="$FAKE_GIT_BIN:/usr/bin:/bin" AGENTIC_TEST_GIT_LOG="$GIT_LOG" "$INSTALLED_BIN" list areas; } 2>"$OUT3")"
assert_output_contains "$LIST_OUTPUT" "software"
assert_exists "$HOME_INSTALLED/.local/share/agentic/repo/areas/software/backend"
assert_file_contains "$GIT_LOG" "git clone https://github.com/sawrus/agent-guides.git $HOME_INSTALLED/.local/share/agentic/repo"

echo "[e2e] Scenario 4: installed mode upgrade runs git pull --ff-only"
OUT4="$TMP_ROOT/upgrade.log"
HOME="$HOME_INSTALLED" PATH="$FAKE_GIT_BIN:/usr/bin:/bin" AGENTIC_TEST_GIT_LOG="$GIT_LOG" AGENTIC_TEST_PULL_AGENTIC_MARKER="upgraded agentic marker" "$INSTALLED_BIN" upgrade >"$OUT4" 2>&1
assert_file_contains "$GIT_LOG" "git -C $HOME_INSTALLED/.local/share/agentic/repo pull --ff-only"
assert_exists "$HOME_INSTALLED/.local/share/agentic/repo/.last-pull"
assert_file_contains "$OUT4" "Updated installed binary: $INSTALLED_BIN"
assert_file_contains "$INSTALLED_BIN" "# upgraded agentic marker"

echo "[e2e] Scenario 4b: managed project upgrade writes detailed changed paths to report"
P4_MANAGED="$TMP_ROOT/project-upgrade-managed"
OUT4_INSTALL="$TMP_ROOT/upgrade-managed-install.log"
OUT4_MANAGED="$TMP_ROOT/upgrade-managed.log"
HOME="$HOME_INSTALLED" AGENTIC_DOCTOR=0 "$INSTALLED_BIN" install \
  --project-dir "$P4_MANAGED" \
  --agent-os opencode \
  --areas software \
  --specializations software.backend \
  --theme=light >"$OUT4_INSTALL" 2>&1
printf '\nmanaged upgrade content\n' >> "$HOME_INSTALLED/.local/share/agentic/repo/areas/software/backend/AGENTS.md"
(
  cd "$P4_MANAGED"
  HOME="$HOME_INSTALLED" PATH="$FAKE_GIT_BIN:/usr/bin:/bin" AGENTIC_TEST_GIT_LOG="$GIT_LOG" AGENTIC_TEST_PULL_AGENTIC_MARKER="managed upgrade marker" AGENTIC_DOCTOR=0 "$INSTALLED_BIN" upgrade
) >"$OUT4_MANAGED" 2>&1
assert_file_contains "$OUT4_MANAGED" "Detected managed project in $P4_MANAGED; syncing from upgraded knowledge base"
assert_file_contains "$OUT4_MANAGED" "Copied/generated paths:"
assert_file_contains "$OUT4_MANAGED" "Changed paths report:"
assert_file_not_contains "$OUT4_MANAGED" "$P4_MANAGED/.opencode/AGENTS.md"
assert_file_not_contains "$OUT4_MANAGED" "$P4_MANAGED/.agent/rules/architecture.md"
assert_file_not_contains "$OUT4_MANAGED" "Copy extension"
assert_file_not_contains "$OUT4_MANAGED" "Copy software.backend/"
assert_file_not_contains "$OUT4_MANAGED" "Skip software.backend/"
REPORT4="$(changed_paths_report_from_output "$OUT4_MANAGED")"
assert_exists "$REPORT4"
assert_file_contains "$REPORT4" "Copied/generated paths ("
assert_file_contains "$REPORT4" "$P4_MANAGED/.opencode/AGENTS.md"

echo "[e2e] Scenario 5: TUI stores theme config and reuses it"
HOME_TUI="$TMP_ROOT/home-tui"
OUT5A="$TMP_ROOT/tui-save-theme.log"
OUT5B="$TMP_ROOT/tui-reuse-theme.log"
NO_FZF_PATH="$TMP_ROOT/no-fzf-bin"
mkdir -p "$NO_FZF_PATH"
P5A="$TMP_ROOT/project-tui-a"
P5B="$TMP_ROOT/project-tui-b"

printf '%s\n' "3" "n" "$P5A" "1" "1" "1" "1" "1" | \
  env HOME="$HOME_TUI" AGENTIC_FORCE_INTERACTIVE=1 AGENTIC_OPENCODE_PROFILE=none PATH="$FAKE_GIT_BIN:$NO_FZF_PATH:$PYTHON_ONLY_BIN:/usr/bin:/bin" AGENTIC_TEST_GIT_LOG="$GIT_LOG" \
  "$INSTALLED_BIN" tui >"$OUT5A" 2>&1

assert_exists "$HOME_TUI/.config/agentic/config"
assert_file_contains "$HOME_TUI/.config/agentic/config" "theme=light"
assert_exists "$HOME_TUI/.local/share/agentic/repo/areas/software/frontend"
assert_exists "$P5A/.agent/rules"
assert_file_contains "$OUT5A" "Theme: light"

printf '%s\n' "n" "$P5B" "1" "1" "1" "1" "1" | \
  env HOME="$HOME_TUI" AGENTIC_FORCE_INTERACTIVE=1 AGENTIC_OPENCODE_PROFILE=none PATH="$FAKE_GIT_BIN:$NO_FZF_PATH:$PYTHON_ONLY_BIN:/usr/bin:/bin" AGENTIC_TEST_GIT_LOG="$GIT_LOG" \
  "$INSTALLED_BIN" tui >"$OUT5B" 2>&1

assert_exists "$P5B/.agent/rules"
assert_file_contains "$OUT5B" "Theme: light"
assert_output_not_contains "$(cat "$OUT5B")" "Select interface theme:"

echo "[e2e] Scenario 5b: TUI asks OpenCode plugins when MCP selection is none"
HOME_TUI_OC_PLUGINS="$TMP_ROOT/home-tui-opencode-plugins"
OUT5B_OC="$TMP_ROOT/tui-opencode-plugins-none.log"
P5B_OC="$TMP_ROOT/project-tui-opencode-plugins-none"

printf '%s\n' "n" "$P5B_OC" "1,2" "1" "1" "1" "n" "" | \
  env HOME="$HOME_TUI_OC_PLUGINS" AGENTIC_FORCE_INTERACTIVE=1 AGENTIC_OPENCODE_PROFILE=none AGENTIC_DOCTOR=0 PATH="$FAKE_GIT_BIN:$NO_FZF_PATH:$PYTHON_ONLY_BIN:/usr/bin:/bin" AGENTIC_TEST_GIT_LOG="$GIT_LOG" \
  "$INSTALLED_BIN" tui --theme=light >"$OUT5B_OC" 2>&1

assert_exists "$HOME_TUI_OC_PLUGINS/.config/agentic/opencode-plugins.json"
assert_file_contains "$OUT5B_OC" "Select optional OpenCode plugin(s):"
assert_file_not_contains "$OUT5B_OC" "agent-model-mapper: choose OpenCode models for Agentic roles"
assert_file_contains "$HOME_TUI_OC_PLUGINS/.config/agentic/opencode-plugins.json" "\"telegram\""
assert_file_contains "$HOME_TUI_OC_PLUGINS/.config/agentic/opencode-plugins.json" "\"agentModelMapper\""
python3 - "$HOME_TUI_OC_PLUGINS/.config/agentic/opencode-plugins.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
if data.get("agentModelMapper", {}).get("enabled") is not False:
    raise SystemExit("agentModelMapper should be disabled")
if data.get("telegram", {}).get("enabled") is not False:
    raise SystemExit("telegram should be disabled")
PY

echo "[e2e] Scenario 5b2: TUI can disable existing OpenCode mapper config"
HOME_TUI_OC_EXISTING="$TMP_ROOT/home-tui-opencode-existing"
OUT5B_EXISTING="$TMP_ROOT/tui-opencode-existing-none.log"
P5B_EXISTING="$TMP_ROOT/project-tui-opencode-existing-none"
mkdir -p "$HOME_TUI_OC_EXISTING/.config/agentic"
cat > "$HOME_TUI_OC_EXISTING/.config/agentic/opencode-plugins.json" <<'JSON'
{
  "telegram": {
    "enabled": false
  },
  "agentModelMapper": {
    "enabled": true
  }
}
JSON

printf '%s\n' "n" "$P5B_EXISTING" "1,2" "1" "1" "1" "n" "" | \
  env HOME="$HOME_TUI_OC_EXISTING" AGENTIC_FORCE_INTERACTIVE=1 AGENTIC_OPENCODE_PROFILE=none AGENTIC_DOCTOR=0 PATH="$FAKE_GIT_BIN:$NO_FZF_PATH:$PYTHON_ONLY_BIN:/usr/bin:/bin" AGENTIC_TEST_GIT_LOG="$GIT_LOG" \
  "$INSTALLED_BIN" tui --theme=light >"$OUT5B_EXISTING" 2>&1

assert_file_contains "$OUT5B_EXISTING" "Select optional OpenCode plugin(s):"
assert_file_not_contains "$OUT5B_EXISTING" "OpenCode plugin config already exists; keeping current settings"
assert_file_not_contains "$OUT5B_EXISTING" "agent-model-mapper: choose OpenCode models for Agentic roles"
assert_file_contains "$HOME_TUI_OC_EXISTING/.config/agentic/opencode-plugins.json" "\"agentModelMapper\""
python3 - "$HOME_TUI_OC_EXISTING/.config/agentic/opencode-plugins.json" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
if data.get("agentModelMapper", {}).get("enabled") is not False:
    raise SystemExit("agentModelMapper should be disabled")
if data.get("telegram", {}).get("enabled") is not False:
    raise SystemExit("telegram should be disabled")
PY

echo "[e2e] Scenario 5c: TUI MCP MemPalace selection runs pip install"
HOME_TUI_MEMPALACE="$TMP_ROOT/home-tui-mempalace"
OUT5C="$TMP_ROOT/tui-mempalace.log"
P5C="$TMP_ROOT/project-tui-mempalace"
FAKE_TUI_MEMPALACE_BIN="$TMP_ROOT/fake-tui-mempalace-bin"
FAKE_TUI_MEMPALACE_PIP_LOG="$TMP_ROOT/fake-tui-mempalace-pip.log"
mkdir -p "$FAKE_TUI_MEMPALACE_BIN"
cat > "$FAKE_TUI_MEMPALACE_BIN/pip" <<'EOS'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${FAKE_TUI_MEMPALACE_PIP_LOG:?missing FAKE_TUI_MEMPALACE_PIP_LOG}"
exit 0
EOS
cat > "$FAKE_TUI_MEMPALACE_BIN/mempalace-mcp" <<'EOS'
#!/usr/bin/env bash
exit 0
EOS
cat > "$FAKE_TUI_MEMPALACE_BIN/mempalace" <<'EOS'
#!/usr/bin/env bash
exit 0
EOS
chmod +x "$FAKE_TUI_MEMPALACE_BIN"/*

printf '%s\n' "n" "$P5C" "2" "3" "1" "1" | \
  env HOME="$HOME_TUI_MEMPALACE" AGENTIC_FORCE_INTERACTIVE=1 AGENTIC_OPENCODE_PROFILE=none AGENTIC_DOCTOR=0 PATH="$FAKE_TUI_MEMPALACE_BIN:$FAKE_GIT_BIN:$NO_FZF_PATH:$PYTHON_ONLY_BIN:/usr/bin:/bin" \
    AGENTIC_TEST_GIT_LOG="$GIT_LOG" FAKE_TUI_MEMPALACE_PIP_LOG="$FAKE_TUI_MEMPALACE_PIP_LOG" \
    "$INSTALLED_BIN" tui --theme=light >"$OUT5C" 2>&1

assert_file_contains "$FAKE_TUI_MEMPALACE_PIP_LOG" "install mempalace"
assert_file_contains "$OUT5C" "MemPalace package installed via 'pip install mempalace'"
assert_file_contains "$P5C/.codex/config.toml" "[features]"
assert_file_contains "$P5C/.codex/config.toml" "memories = true"
assert_file_contains "$P5C/.codex/config.toml" "[mcp_servers.mempalace]"

echo "[e2e] Scenario 6: TUI with available fzf uses dark fzf palette in --theme=dark mode"
HOME_TUI_FZF="$TMP_ROOT/home-tui-fzf"
OUT6="$TMP_ROOT/tui-fzf-dark.log"
P6="$TMP_ROOT/project-tui-fzf-dark"
FAKE_FZF_BIN="$TMP_ROOT/fake-fzf-bin"
FZF_CALLS_LOG="$TMP_ROOT/fzf-calls.log"
mkdir -p "$FAKE_FZF_BIN"

cat > "$FAKE_FZF_BIN/fzf" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
LOG_FILE="${AGENTIC_TEST_FZF_CALLS_LOG:?missing AGENTIC_TEST_FZF_CALLS_LOG}"
printf 'fzf %s\n' "$*" >> "$LOG_FILE"

# Drain stdin fully so the producer side of the pipe does not fail with SIGPIPE.
cat >/dev/null || true

case "$*" in
  *"Target project directory [/tmp/agentic-project]: "*)
    printf '%s\n' "${AGENTIC_TEST_FZF_DIR_QUERY_RESULT:-}" "/tmp/agentic-project"
    ;;
  *"Select Agent OS target(s): "*)
    printf '%s\n' "opencode"
    ;;
  *"Select area(s): "*)
    printf '%s\n' "software"
    ;;
  *"Select specialization(s) for 'software': "*)
    printf '%s\n' "backend"
    ;;
  *)
    printf '%s\n' "default"
    ;;
esac
EOS
chmod +x "$FAKE_FZF_BIN/fzf"

env HOME="$HOME_TUI_FZF" AGENTIC_FORCE_INTERACTIVE=1 AGENTIC_OPENCODE_PROFILE=none PATH="$FAKE_FZF_BIN:$FAKE_GIT_BIN:$PYTHON_ONLY_BIN:/usr/bin:/bin" \
  AGENTIC_TEST_GIT_LOG="$GIT_LOG" AGENTIC_TEST_FZF_CALLS_LOG="$FZF_CALLS_LOG" \
  AGENTIC_TEST_FZF_DIR_QUERY_RESULT="$P6" \
  "$INSTALLED_BIN" tui --theme=dark >"$OUT6" 2>&1

assert_exists "$P6/.agent/rules"
assert_file_contains "$FZF_CALLS_LOG" "Target project directory [/tmp/agentic-project]:"
assert_file_contains "$FZF_CALLS_LOG" "Select Agent OS target(s):"
assert_file_contains "$FZF_CALLS_LOG" "Select optional MCP integration(s):"
assert_file_contains "$FZF_CALLS_LOG" "Select area(s):"
assert_file_contains "$FZF_CALLS_LOG" "Select specialization(s) for 'software':"
assert_file_contains "$FZF_CALLS_LOG" "--color=fg:#e5e7eb,bg:#111827,hl:#60a5fa"
assert_file_contains "$FZF_CALLS_LOG" "--color=fg+:#ffffff,bg+:#1f2937,hl+:#93c5fd"
assert_file_contains "$FZF_CALLS_LOG" "--color=query:#e5e7eb,prompt:#22c55e,pointer:#f97316,marker:#a3e635,spinner:#06b6d4,header:#d1d5db"

REAL_FZF_BIN="$(command -v fzf || true)"
if [[ -n "$REAL_FZF_BIN" ]] && [[ -t 0 ]] && [[ -t 1 ]]; then
  echo "[e2e] Scenario 7: real fzf blackbox accepts typed directory query"
  HOME_TUI_REAL_FZF="$TMP_ROOT/home-tui-real-fzf"
  OUT7="$TMP_ROOT/tui-real-fzf.log"
  P7="$TMP_ROOT/project-tui-real-fzf"
  REAL_FZF_PROXY_BIN="$TMP_ROOT/real-fzf-proxy-bin"
  mkdir -p "$REAL_FZF_PROXY_BIN"

  cat > "$REAL_FZF_PROXY_BIN/fzf" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
REAL_FZF="${AGENTIC_TEST_REAL_FZF_BIN:?missing AGENTIC_TEST_REAL_FZF_BIN}"

case "$*" in
  *"Target project directory [/tmp/agentic-project]: "*)
    exec "$REAL_FZF" "$@" --filter "${AGENTIC_TEST_FZF_DIR_QUERY_RESULT:-}"
    ;;
  *"Select Agent OS target(s): "*)
    exec "$REAL_FZF" "$@" --filter "opencode"
    ;;
  *"Select area(s): "*)
    exec "$REAL_FZF" "$@" --filter "software"
    ;;
  *"Select specialization(s) for 'software': "*)
    exec "$REAL_FZF" "$@" --filter "backend"
    ;;
  *)
    exec "$REAL_FZF" "$@"
    ;;
esac
EOS
  chmod +x "$REAL_FZF_PROXY_BIN/fzf"

  env HOME="$HOME_TUI_REAL_FZF" AGENTIC_FORCE_INTERACTIVE=1 AGENTIC_OPENCODE_PROFILE=none PATH="$REAL_FZF_PROXY_BIN:$FAKE_GIT_BIN:$PYTHON_ONLY_BIN:/usr/bin:/bin" \
    AGENTIC_TEST_GIT_LOG="$GIT_LOG" AGENTIC_TEST_REAL_FZF_BIN="$REAL_FZF_BIN" \
    AGENTIC_TEST_FZF_DIR_QUERY_RESULT="$P7" \
    "$INSTALLED_BIN" tui --theme=dark >"$OUT7" 2>&1

  assert_exists "$P7/.agent/rules"
else
  echo "[e2e] Scenario 7 skipped: requires real fzf and an interactive TTY"
fi

echo "[e2e] Scenario 8: real opencode blackbox MemPalace verification"
REAL_OPENCODE_BIN="$(command -v opencode || true)"
if [[ -z "${AGENTIC_TEST_CLI:-}" && -n "$REAL_OPENCODE_BIN" ]] && python3 -m mempalace --help >/dev/null 2>&1; then
  P8_NEG="$TMP_ROOT/project-opencode-mempalace-negative"
  P8_POS="$TMP_ROOT/project-opencode-mempalace-positive"
  OUT8_NEG="$TMP_ROOT/opencode-mempalace-negative.log"
  OUT8_POS="$TMP_ROOT/opencode-mempalace-positive.log"

  # Install for opencode with backend + general specs.
  HOME="$TMP_ROOT/home-opencode-bb" AGENTIC_ENABLE_MEMPALACE=y AGENTIC_DOCTOR=0 "$CLI" install \
    --project-dir "$P8_NEG" \
    --agent-os opencode \
    --areas software \
    --specializations software.backend,software.general \
    --theme=light >/dev/null 2>&1

  HOME="$TMP_ROOT/home-opencode-bb" AGENTIC_ENABLE_MEMPALACE=y AGENTIC_DOCTOR=0 "$CLI" install \
    --project-dir "$P8_POS" \
    --agent-os opencode \
    --areas software \
    --specializations software.backend,software.general \
    --theme=light >/dev/null 2>&1

  # Force negative case by removing MemPalace entry from opencode local config.
  python3 - "$P8_NEG/opencode.json" <<'PYCODE'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
if isinstance(data.get("mcp"), dict):
    data["mcp"].pop("mempalace", None)
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PYCODE

  # Run real opencode binary in both projects.
  # Override command can be supplied to adapt to local opencode versions:
  #   AGENTIC_TEST_OPENCODE_VERIFY_CMD='opencode "<prompt text>"'
  OPENCODE_VERIFY_CMD="${AGENTIC_TEST_OPENCODE_VERIFY_CMD:-opencode \"List connected MCP servers by configured server name.\"}"
  (cd "$P8_NEG" && eval "$OPENCODE_VERIFY_CMD") >"$OUT8_NEG" 2>&1 || true
  (cd "$P8_POS" && eval "$OPENCODE_VERIFY_CMD") >"$OUT8_POS" 2>&1 || true

  # Patterns can be customized for different opencode outputs.
  POS_PATTERN="${AGENTIC_TEST_OPENCODE_MEMPALACE_POS_PATTERN:-mempalace}"
  NEG_PATTERN="${AGENTIC_TEST_OPENCODE_MEMPALACE_NEG_PATTERN:-mempalace}"

  assert_file_not_contains "$OUT8_NEG" "$NEG_PATTERN"
  assert_file_contains "$OUT8_POS" "$POS_PATTERN"
else
  echo "[e2e] Scenario 8 skipped: requires direct CLI, real 'opencode' binary, and working 'python3 -m mempalace'"
fi

echo "[e2e] Scenario 9: install with mempalace enabled runs mempalace init"
HOME_INIT="$TMP_ROOT/home-mempalace-init"
P9="$TMP_ROOT/project-mempalace-init"
P9_REAL="$TMP_ROOT_REAL/project-mempalace-init"
FAKE_INIT_BIN="$TMP_ROOT/fake-init-mempalace-bin"
MEMPALACE_INIT_LOG="$TMP_ROOT/mempalace-init-calls.log"
FAKE_INIT_PIP_LOG="$TMP_ROOT/fake-init-pip.log"
mkdir -p "$FAKE_INIT_BIN"
: > "$MEMPALACE_INIT_LOG"
: > "$FAKE_INIT_PIP_LOG"

cat > "$FAKE_INIT_BIN/mempalace" <<'EOS'
#!/usr/bin/env bash
printf 'mempalace %s\n' "$*" >> "${MEMPALACE_INIT_LOG:?}"
exit 0
EOS
cat > "$FAKE_INIT_BIN/mempalace-mcp" <<'EOS'
#!/usr/bin/env bash
exit 0
EOS
cat > "$FAKE_INIT_BIN/pip" <<'EOS'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${FAKE_INIT_PIP_LOG:?}"
exit 0
EOS
chmod +x "$FAKE_INIT_BIN"/*
mkdir -p "$P9/docs"
printf '%s\n' "# Shared Docs" > "$P9/docs/README.md"

OUT9="$TMP_ROOT/mempalace-init-install.log"
HOME="$HOME_INIT" AGENTIC_ENABLE_MEMPALACE=y AGENTIC_DOCTOR=0 \
  PATH="$FAKE_INIT_BIN:$FAKE_GIT_BIN:$PYTHON_ONLY_BIN:/usr/bin:/bin" \
  AGENTIC_TEST_GIT_LOG="$GIT_LOG" \
  MEMPALACE_INIT_LOG="$MEMPALACE_INIT_LOG" \
  FAKE_INIT_PIP_LOG="$FAKE_INIT_PIP_LOG" \
  "$CLI" install \
    --project-dir "$P9" \
    --agent-os opencode \
    --areas software \
    --specializations software.backend \
    --theme=light >"$OUT9" 2>&1

# Verify mempalace init/mining uses low-budget, wing-aware commands
assert_file_contains "$MEMPALACE_INIT_LOG" "mempalace init $P9_REAL --yes --no-llm"
assert_file_contains "$MEMPALACE_INIT_LOG" "mempalace mine $P9_REAL --wing project_mempalace_init"
assert_file_contains "$MEMPALACE_INIT_LOG" "mempalace mine $P9_REAL/docs --wing shared_docs"
# Should NOT show fallback instructions since init succeeded
assert_output_not_contains "$(cat "$OUT9")" "Optional MemPalace project indexing instructions"
# Manifest should contain mcp_integrations with mempalace
assert_file_contains "$P9/.agentic.json" '"mcp_integrations"'
assert_file_contains "$P9/.agentic.json" '"mempalace"'

echo "[e2e] Scenario 9b: mempalace init timeout does not hang install"
HOME_TIMEOUT="$TMP_ROOT/home-mempalace-timeout"
P9_TIMEOUT="$TMP_ROOT/project-mempalace-timeout"
P9_TIMEOUT_REAL="$TMP_ROOT_REAL/project-mempalace-timeout"
FAKE_TIMEOUT_BIN="$TMP_ROOT/fake-timeout-mempalace-bin"
MEMPALACE_TIMEOUT_LOG="$TMP_ROOT/mempalace-timeout-calls.log"
FAKE_TIMEOUT_PIP_LOG="$TMP_ROOT/fake-timeout-pip.log"
mkdir -p "$FAKE_TIMEOUT_BIN"
: > "$MEMPALACE_TIMEOUT_LOG"
: > "$FAKE_TIMEOUT_PIP_LOG"

cat > "$FAKE_TIMEOUT_BIN/mempalace" <<'EOS'
#!/usr/bin/env bash
printf 'mempalace %s\n' "$*" >> "${MEMPALACE_TIMEOUT_LOG:?}"
if [[ "${1:-}" == "init" ]]; then
  sleep 5
fi
exit 0
EOS
cat > "$FAKE_TIMEOUT_BIN/mempalace-mcp" <<'EOS'
#!/usr/bin/env bash
exit 0
EOS
cat > "$FAKE_TIMEOUT_BIN/pip" <<'EOS'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${FAKE_TIMEOUT_PIP_LOG:?}"
exit 0
EOS
chmod +x "$FAKE_TIMEOUT_BIN"/*

OUT9_TIMEOUT="$TMP_ROOT/mempalace-timeout-install.log"
HOME="$HOME_TIMEOUT" AGENTIC_ENABLE_MEMPALACE=y AGENTIC_DOCTOR=0 AGENTIC_MEMPALACE_TIMEOUT_SECONDS=1 \
  PATH="$FAKE_TIMEOUT_BIN:$FAKE_GIT_BIN:$PYTHON_ONLY_BIN:/usr/bin:/bin" \
  AGENTIC_TEST_GIT_LOG="$GIT_LOG" \
  MEMPALACE_TIMEOUT_LOG="$MEMPALACE_TIMEOUT_LOG" \
  FAKE_TIMEOUT_PIP_LOG="$FAKE_TIMEOUT_PIP_LOG" \
  "$CLI" install \
    --project-dir "$P9_TIMEOUT" \
    --agent-os codex \
    --areas software \
    --specializations software.backend \
    --theme=light >"$OUT9_TIMEOUT" 2>&1

assert_file_contains "$MEMPALACE_TIMEOUT_LOG" "mempalace init $P9_TIMEOUT_REAL --yes --no-llm"
assert_file_contains "$OUT9_TIMEOUT" "Timed out after 1s:"
assert_file_contains "$OUT9_TIMEOUT" "$P9_TIMEOUT_REAL"
assert_file_contains "$OUT9_TIMEOUT" "Optional MemPalace project indexing instructions for target project: $P9_TIMEOUT_REAL"
assert_file_contains "$P9_TIMEOUT/.codex/config.toml" "[features]"
assert_file_contains "$P9_TIMEOUT/.codex/config.toml" "memories = true"
assert_file_contains "$P9_TIMEOUT/.codex/config.toml" "[mcp_servers.mempalace]"

echo "[e2e] Scenario 10: mempalace enabled but binary missing shows fallback instructions"
HOME_FAIL="$TMP_ROOT/home-mempalace-fail"
P10="$TMP_ROOT/project-mempalace-fail"
FAKE_FAIL_BIN="$TMP_ROOT/fake-fail-mempalace-bin"
FAKE_FAIL_PIP_LOG="$TMP_ROOT/fake-fail-pip.log"
mkdir -p "$FAKE_FAIL_BIN"
: > "$FAKE_FAIL_PIP_LOG"

# pip succeeds but mempalace/mempalace-mcp not on PATH after pip install
cat > "$FAKE_FAIL_BIN/pip" <<'EOS'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${FAKE_FAIL_PIP_LOG:?}"
exit 0
EOS
chmod +x "$FAKE_FAIL_BIN"/*

OUT10="$TMP_ROOT/mempalace-fail-install.log"
HOME="$HOME_FAIL" AGENTIC_ENABLE_MEMPALACE=y AGENTIC_DOCTOR=0 \
  PATH="$FAKE_FAIL_BIN:$FAKE_GIT_BIN:$PYTHON_ONLY_BIN:/usr/bin:/bin" \
  AGENTIC_TEST_GIT_LOG="$GIT_LOG" \
  FAKE_FAIL_PIP_LOG="$FAKE_FAIL_PIP_LOG" \
  "$CLI" install \
    --project-dir "$P10" \
    --agent-os opencode \
    --areas software \
    --specializations software.backend \
    --theme=light >"$OUT10" 2>&1

# Should show fallback instructions since mempalace binary not found after pip install
assert_file_contains "$OUT10" "Optional MemPalace project indexing instructions"
assert_file_contains "$OUT10" "pip install mempalace"

echo "[e2e] Scenario 11: upgrade with manifest skips MCP prompts and re-applies config"
HOME_UPGRADE="$TMP_ROOT/home-upgrade-mcp"
P11="$TMP_ROOT/project-upgrade-mcp"
P11_REAL="$TMP_ROOT_REAL/project-upgrade-mcp"
FAKE_UPGRADE_BIN="$TMP_ROOT/fake-upgrade-mcp-bin"
MEMPALACE_UPGRADE_LOG="$TMP_ROOT/mempalace-upgrade-calls.log"
FAKE_UPGRADE_PIP_LOG="$TMP_ROOT/fake-upgrade-pip.log"
mkdir -p "$FAKE_UPGRADE_BIN"
: > "$MEMPALACE_UPGRADE_LOG"
: > "$FAKE_UPGRADE_PIP_LOG"

# Create fake mempalace binaries that log calls
cat > "$FAKE_UPGRADE_BIN/mempalace" <<'EOS'
#!/usr/bin/env bash
printf 'mempalace %s\n' "$*" >> "${MEMPALACE_UPGRADE_LOG:?}"
exit 0
EOS
cat > "$FAKE_UPGRADE_BIN/mempalace-mcp" <<'EOS'
#!/usr/bin/env bash
exit 0
EOS
cat > "$FAKE_UPGRADE_BIN/pip" <<'EOS'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${FAKE_UPGRADE_PIP_LOG:?}"
exit 0
EOS
chmod +x "$FAKE_UPGRADE_BIN"/*
mkdir -p "$P11/docs"
printf '%s\n' "# Upgrade Docs" > "$P11/docs/README.md"

# First do a normal install with mempalace+context7 enabled to create manifest
OUT11_INSTALL="$TMP_ROOT/upgrade-mcp-install.log"
HOME="$HOME_UPGRADE" AGENTIC_ENABLE_MEMPALACE=y AGENTIC_ENABLE_CONTEXT7=y AGENTIC_DOCTOR=0 \
  PATH="$FAKE_UPGRADE_BIN:$FAKE_GIT_BIN:$PYTHON_ONLY_BIN:/usr/bin:/bin" \
  AGENTIC_TEST_GIT_LOG="$GIT_LOG" \
  MEMPALACE_UPGRADE_LOG="$MEMPALACE_UPGRADE_LOG" \
  FAKE_UPGRADE_PIP_LOG="$FAKE_UPGRADE_PIP_LOG" \
  "$CLI" install \
    --project-dir "$P11" \
    --agent-os opencode \
    --areas software \
    --specializations software.backend \
    --theme=light >"$OUT11_INSTALL" 2>&1

# Verify manifest has mcp_integrations
assert_file_contains "$P11/.agentic.json" '"mcp_integrations"'
assert_file_contains "$P11/.agentic.json" '"mempalace"'
assert_file_contains "$P11/.agentic.json" '"context7"'

# Now simulate re-install (what sync_current_project_after_upgrade does) - NO env vars for MCP
# The manifest should auto-restore them
OUT11="$TMP_ROOT/upgrade-mcp-reinstall.log"
: > "$MEMPALACE_UPGRADE_LOG"
HOME="$HOME_UPGRADE" AGENTIC_DOCTOR=0 \
  PATH="$FAKE_UPGRADE_BIN:$FAKE_GIT_BIN:$PYTHON_ONLY_BIN:/usr/bin:/bin" \
  AGENTIC_TEST_GIT_LOG="$GIT_LOG" \
  MEMPALACE_UPGRADE_LOG="$MEMPALACE_UPGRADE_LOG" \
  FAKE_UPGRADE_PIP_LOG="$FAKE_UPGRADE_PIP_LOG" \
  "$CLI" install \
    --project-dir "$P11" \
    --agent-os opencode \
    --areas software \
    --specializations software.backend \
    --theme=light >"$OUT11" 2>&1

# Should NOT contain interactive prompt text (prompts skipped due to restored settings)
assert_output_not_contains "$(cat "$OUT11")" "Enable MemPalace MCP memory integration? [y/N]:"
assert_output_not_contains "$(cat "$OUT11")" "Enable Context7 MCP configuration? [y/N]:"
assert_output_not_contains "$(cat "$OUT11")" "Select optional OpenCode plugin(s):"
# Should have run mempalace init/mining (since mempalace was enabled)
assert_file_contains "$MEMPALACE_UPGRADE_LOG" "mempalace init $P11_REAL --yes --no-llm"
assert_file_contains "$MEMPALACE_UPGRADE_LOG" "mempalace mine $P11_REAL --wing project_upgrade_mcp"
assert_file_contains "$MEMPALACE_UPGRADE_LOG" "mempalace mine $P11_REAL/docs --wing shared_docs"

echo "[e2e] Scenario 12: opencode_mapper_discover_models finds provider models"
HOME_MODELS="$TMP_ROOT/home-models"
mkdir -p "$HOME_MODELS/.config/opencode"
cat > "$HOME_MODELS/.config/opencode/opencode.json" <<'MODELJSON'
{
  "provider": {
    "google": {
      "models": {
        "antigravity-claude-sonnet-4-6": {"name": "Claude Sonnet 4.6"},
        "antigravity-gemini-3-flash": {"name": "Gemini 3 Flash"}
      }
    },
    "openai": {
      "models": {
        "gpt-5.4": {"name": "GPT 5.4"}
      }
    }
  },
  "agent": {
    "developer": {
      "model": "google/antigravity-claude-sonnet-4-6",
      "fallback": ["opencode/minimax-m2.5-free"]
    }
  }
}
MODELJSON

OUT12="$TMP_ROOT/discover-models.log"
# Test the Python logic from opencode_mapper_discover_models directly
python3 - "$HOME_MODELS/.config/opencode/opencode.json" >"$OUT12" 2>&1 <<'PY'
import json
import sys
from pathlib import Path

fallback = ["opencode/minimax-m2.5-free"]
path = Path(sys.argv[1])
models = []

def collect_provider_models(data):
    """Extract models from provider.<name>.models dict keys."""
    providers = data.get("provider")
    if not isinstance(providers, dict):
        return
    for provider_name, provider_data in providers.items():
        if not isinstance(provider_data, dict):
            continue
        provider_models = provider_data.get("models")
        if not isinstance(provider_models, dict):
            continue
        for model_name in provider_models:
            if isinstance(model_name, str) and model_name.strip():
                models.append(f"{provider_name}/{model_name}")

def collect(value):
    if isinstance(value, list):
        for item in value:
            collect(item)
        return
    if not isinstance(value, dict):
        return
    for key, item in value.items():
        if key in {"model", "id"} and isinstance(item, str) and "/" in item:
            models.append(item)
        if key == "fallback" and isinstance(item, list):
            models.extend(model for model in item if isinstance(model, str))
        collect(item)

try:
    data = json.loads(path.read_text(encoding="utf-8"))
    collect_provider_models(data)
    collect(data)
except Exception:
    pass

seen = set()
for model in models or fallback:
    model = model.strip()
    if model and model not in seen:
        seen.add(model)
        print(model)
PY

assert_file_contains "$OUT12" "google/antigravity-claude-sonnet-4-6"
assert_file_contains "$OUT12" "google/antigravity-gemini-3-flash"
assert_file_contains "$OUT12" "openai/gpt-5.4"
assert_file_contains "$OUT12" "opencode/minimax-m2.5-free"

echo "[e2e] All scenarios passed"
