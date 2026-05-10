#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
CLI="$ROOT_DIR/agentic"
export AGENTIC_TEST_SOURCE_AGENTIC="$CLI"
TMP_ROOT="$(mktemp -d /tmp/agentic-e2e.XXXXXX)"
PYTHON_ONLY_BIN="$TMP_ROOT/python-bin"
mkdir -p "$PYTHON_ONLY_BIN"
ln -s "$(command -v python3)" "$PYTHON_ONLY_BIN/python3"
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
Dynamic loading of guidance
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
  cp "$AGENTIC_TEST_SOURCE_AGENTIC" "$dest/agentic"
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

echo "[e2e] Scenario 1: dev mode install from repository checkout persists --theme=<value> to config"
P1="$TMP_ROOT/project-dev-install"
HOME_DEV_INSTALL="$TMP_ROOT/home-dev-install"
HOME="$HOME_DEV_INSTALL" "$CLI" install \
  --project-dir "$P1" \
  --agent-os opencode \
  --areas software \
  --specializations software.backend \
  --theme=light

assert_exists "$P1/.opencode"
assert_exists "$P1/.agent/rules"
assert_exists "$P1/.agent/skills"
assert_exists "$P1/.agent/workflows"
assert_exists "$P1/.agent/prompts"
assert_not_exists "$P1/AGENTS.md"
assert_exists "$P1/.opencode/AGENTS.md"
assert_file_contains "$P1/.opencode/AGENTS.md" "software/backend"
assert_file_contains "$P1/.opencode/AGENTS.md" "Dynamic loading of guidance"
assert_file_contains "$P1/.opencode/AGENTS.md" "generated_by: agentic"
assert_exists "$P1/.agentic.json"
assert_file_contains "$P1/.agentic.json" "\"managed_files\""
assert_file_contains "$P1/.agentic.json" ".opencode/AGENTS.md"
assert_file_contains "$P1/.agentic.json" "https://github.com/sawrus/agent-guides"
assert_file_not_contains "$P1/.opencode/opencode.json" "\"context7\""
assert_file_contains "$P1/.opencode/plugins/telegram-notification.ts" "Generated by agentic"
assert_exists "$HOME_DEV_INSTALL/.config/agentic/opencode-plugins.json"
assert_file_contains "$HOME_DEV_INSTALL/.config/agentic/opencode-plugins.json" "\"enabled\": false"
assert_exists "$HOME_DEV_INSTALL/.config/agentic/config"
assert_file_contains "$HOME_DEV_INSTALL/.config/agentic/config" "theme=light"

echo "[e2e] Scenario 1ab: MemPalace runtime check passes when mempalace-mcp is available"
P1_MEM_OK="$TMP_ROOT/project-mempalace-ok"
HOME_MEM_OK="$TMP_ROOT/home-mempalace-ok"
OUT1AB_OK="$TMP_ROOT/project-mempalace-ok.log"
FAKE_MEMPALACE_BIN="$TMP_ROOT/fake-mempalace-bin"
mkdir -p "$FAKE_MEMPALACE_BIN"
cat > "$FAKE_MEMPALACE_BIN/mempalace-mcp" <<'EOS'
#!/usr/bin/env bash
exit 0
EOS
chmod +x "$FAKE_MEMPALACE_BIN/mempalace-mcp"

env HOME="$HOME_MEM_OK" PATH="$FAKE_MEMPALACE_BIN:$PATH" AGENTIC_ENABLE_MEMPALACE=y "$CLI" install \
  --project-dir "$P1_MEM_OK" \
  --agent-os codex \
  --areas software \
  --specializations software.backend \
  --theme=light >"$OUT1AB_OK" 2>&1
assert_file_contains "$OUT1AB_OK" "MemPalace MCP runtime check succeeded via 'mempalace-mcp'"
assert_file_contains "$P1_MEM_OK/.codex/config.toml" "[mcp_servers.mempalace]"
assert_file_contains "$OUT1AB_OK" "MemPalace setup instructions for target project:"
assert_file_contains "$OUT1AB_OK" "pip install mempalace"

echo "[e2e] Scenario 1ac: MemPalace runtime check warns and install continues when module is unavailable"
P1_MEM_WARN="$TMP_ROOT/project-mempalace-warn"
HOME_MEM_WARN="$TMP_ROOT/home-mempalace-warn"
OUT1AB_WARN="$TMP_ROOT/project-mempalace-warn.log"
env HOME="$HOME_MEM_WARN" AGENTIC_ENABLE_MEMPALACE=y "$CLI" install \
  --project-dir "$P1_MEM_WARN" \
  --agent-os codex \
  --areas software \
  --specializations software.backend \
  --theme=light >"$OUT1AB_WARN" 2>&1
assert_file_contains "$OUT1AB_WARN" "mempalace-mcp is unavailable; install/repair MemPalace and re-run setup"
assert_file_contains "$P1_MEM_WARN/.codex/config.toml" "[mcp_servers.mempalace]"
assert_file_contains "$OUT1AB_WARN" "MemPalace setup instructions for target project:"

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
printf '%s\n' "y" "test-context7-key" | \
  env HOME="$HOME_CTX" AGENTIC_FORCE_INTERACTIVE=1 "$CLI" install \
    --project-dir "$P1_CTX" \
    --agent-os codex \
    --areas software \
    --specializations software.backend \
    --theme=light >"$OUT1A" 2>&1
assert_file_contains "$P1_CTX/.codex/config.toml" "[mcp_servers.context7]"
assert_file_contains "$P1_CTX/.codex/config.toml" "test-context7-key"

P1_CTX_EMPTY="$TMP_ROOT/project-context7-empty-key"
OUT1A_EMPTY="$TMP_ROOT/project-context7-empty-key.log"
printf '%s\n' "y" "" | \
  env HOME="$HOME_CTX" AGENTIC_FORCE_INTERACTIVE=1 "$CLI" install \
    --project-dir "$P1_CTX_EMPTY" \
    --agent-os codex \
    --areas software \
    --specializations software.backend \
    --theme=light >"$OUT1A_EMPTY" 2>&1
assert_file_contains "$P1_CTX_EMPTY/.codex/config.toml" "[mcp_servers.context7]"
assert_file_not_contains "$P1_CTX_EMPTY/.codex/config.toml" "CONTEXT7_API_KEY"

echo "[e2e] Scenario 1b1: Context7 writes antigravity-specific path"
P1_CTX_MULTI="$TMP_ROOT/project-context7-antigravity"
OUT1A_MULTI="$TMP_ROOT/project-context7-antigravity.log"
printf '%s\n' "y" "" | \
  env HOME="$HOME_CTX" AGENTIC_FORCE_INTERACTIVE=1 "$CLI" install \
    --project-dir "$P1_CTX_MULTI" \
    --agent-os antigravity \
    --areas software \
    --specializations software.backend \
    --theme=light >"$OUT1A_MULTI" 2>&1
assert_file_contains "$HOME_CTX/.gemini/antigravity/mcp_config.json" "\"context7\""
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
assert_file_contains "$P1_CTX_ENV/.codex/config.toml" "[mcp_servers.context7]"
assert_file_contains "$P1_CTX_ENV/.codex/config.toml" "env-context7-key"

echo "[e2e] Scenario 1b3: interactive OpenCode plugin multi-select enables model-checker only"
P1_OC_PLUGINS="$TMP_ROOT/project-opencode-plugins"
HOME_OC_PLUGINS="$TMP_ROOT/home-opencode-plugins"
OUT1A_OC_PLUGINS="$TMP_ROOT/project-opencode-plugins.log"
printf '%s\n' "n" "2" "n" "n" | \
  env HOME="$HOME_OC_PLUGINS" AGENTIC_FORCE_INTERACTIVE=1 PATH="$FAKE_GIT_BIN:$PYTHON_ONLY_BIN:/usr/bin:/bin" "$CLI" install \
    --project-dir "$P1_OC_PLUGINS" \
    --agent-os opencode \
    --areas software \
    --specializations software.backend \
    --theme=light >"$OUT1A_OC_PLUGINS" 2>&1
assert_exists "$HOME_OC_PLUGINS/.config/agentic/opencode-plugins.json"
assert_file_contains "$HOME_OC_PLUGINS/.config/agentic/opencode-plugins.json" "\"enabled\": true"
assert_file_contains "$HOME_OC_PLUGINS/.config/agentic/opencode-plugins.json" "\"modelChecker\""
assert_file_contains "$HOME_OC_PLUGINS/.config/agentic/opencode-plugins.json" "\"telegram\""
assert_file_contains "$HOME_OC_PLUGINS/.config/agentic/opencode-plugins.json" "\"botToken\": \"\""
assert_file_not_contains "$OUT1A_OC_PLUGINS" "Telegram bot token (empty disables plugin):"

echo "[e2e] Scenario 1b4: interactive OpenCode plugin multi-select with no selection does not request Telegram credentials"
P1_OC_NO_PLUGINS="$TMP_ROOT/project-opencode-no-plugins"
HOME_OC_NO_PLUGINS="$TMP_ROOT/home-opencode-no-plugins"
OUT1A_OC_NO_PLUGINS="$TMP_ROOT/project-opencode-no-plugins.log"
printf '%s\n' "n" "" "n" "n" | \
  env HOME="$HOME_OC_NO_PLUGINS" AGENTIC_FORCE_INTERACTIVE=1 PATH="$FAKE_GIT_BIN:$PYTHON_ONLY_BIN:/usr/bin:/bin" "$CLI" install \
    --project-dir "$P1_OC_NO_PLUGINS" \
    --agent-os opencode \
    --areas software \
    --specializations software.backend \
    --theme=light >"$OUT1A_OC_NO_PLUGINS" 2>&1
assert_exists "$HOME_OC_NO_PLUGINS/.config/agentic/opencode-plugins.json"
assert_file_contains "$HOME_OC_NO_PLUGINS/.config/agentic/opencode-plugins.json" "\"telegram\""
assert_file_contains "$HOME_OC_NO_PLUGINS/.config/agentic/opencode-plugins.json" "\"enabled\": false"
assert_file_not_contains "$OUT1A_OC_NO_PLUGINS" "Telegram bot token (empty disables plugin):"

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

echo "[e2e] Scenario 5: TUI stores theme config and reuses it"
HOME_TUI="$TMP_ROOT/home-tui"
OUT5A="$TMP_ROOT/tui-save-theme.log"
OUT5B="$TMP_ROOT/tui-reuse-theme.log"
NO_FZF_PATH="$TMP_ROOT/no-fzf-bin"
mkdir -p "$NO_FZF_PATH"
P5A="$TMP_ROOT/project-tui-a"
P5B="$TMP_ROOT/project-tui-b"

printf '%s\n' "3" "n" "$P5A" "1" "1" "1" "1" "1" | \
  env HOME="$HOME_TUI" AGENTIC_FORCE_INTERACTIVE=1 PATH="$FAKE_GIT_BIN:$NO_FZF_PATH:$PYTHON_ONLY_BIN:/usr/bin:/bin" AGENTIC_TEST_GIT_LOG="$GIT_LOG" \
  "$INSTALLED_BIN" tui >"$OUT5A" 2>&1

assert_exists "$HOME_TUI/.config/agentic/config"
assert_file_contains "$HOME_TUI/.config/agentic/config" "theme=light"
assert_exists "$HOME_TUI/.local/share/agentic/repo/areas/software/frontend"
assert_exists "$P5A/.agent/rules"
assert_file_contains "$OUT5A" "Theme: light"

printf '%s\n' "n" "$P5B" "1" "1" "1" "1" "1" | \
  env HOME="$HOME_TUI" AGENTIC_FORCE_INTERACTIVE=1 PATH="$FAKE_GIT_BIN:$NO_FZF_PATH:$PYTHON_ONLY_BIN:/usr/bin:/bin" AGENTIC_TEST_GIT_LOG="$GIT_LOG" \
  "$INSTALLED_BIN" tui >"$OUT5B" 2>&1

assert_exists "$P5B/.agent/rules"
assert_file_contains "$OUT5B" "Theme: light"
assert_output_not_contains "$(cat "$OUT5B")" "Select interface theme:"

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
    printf '%s\n' "default"
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

env HOME="$HOME_TUI_FZF" AGENTIC_FORCE_INTERACTIVE=1 PATH="$FAKE_FZF_BIN:$FAKE_GIT_BIN:$PYTHON_ONLY_BIN:/usr/bin:/bin" \
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
    exec "$REAL_FZF" "$@" --filter "default"
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

  env HOME="$HOME_TUI_REAL_FZF" AGENTIC_FORCE_INTERACTIVE=1 PATH="$REAL_FZF_PROXY_BIN:$FAKE_GIT_BIN:$PYTHON_ONLY_BIN:/usr/bin:/bin" \
    AGENTIC_TEST_GIT_LOG="$GIT_LOG" AGENTIC_TEST_REAL_FZF_BIN="$REAL_FZF_BIN" \
    AGENTIC_TEST_FZF_DIR_QUERY_RESULT="$P7" \
    "$INSTALLED_BIN" tui --theme=dark >"$OUT7" 2>&1

  assert_exists "$P7/.agent/rules"
else
  echo "[e2e] Scenario 7 skipped: requires real fzf and an interactive TTY"
fi

echo "[e2e] Scenario 8: real opencode blackbox MemPalace verification"
REAL_OPENCODE_BIN="$(command -v opencode || true)"
if [[ -n "$REAL_OPENCODE_BIN" ]] && python3 -m mempalace --help >/dev/null 2>&1; then
  P8_NEG="$TMP_ROOT/project-opencode-mempalace-negative"
  P8_POS="$TMP_ROOT/project-opencode-mempalace-positive"
  OUT8_NEG="$TMP_ROOT/opencode-mempalace-negative.log"
  OUT8_POS="$TMP_ROOT/opencode-mempalace-positive.log"

  # Install for opencode with backend + general specs.
  HOME="$TMP_ROOT/home-opencode-bb" "$CLI" install \
    --project-dir "$P8_NEG" \
    --agent-os opencode \
    --areas software \
    --specializations software.backend,software.general \
    --theme=light >/dev/null 2>&1

  HOME="$TMP_ROOT/home-opencode-bb" "$CLI" install \
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
  OPENCODE_VERIFY_CMD="${AGENTIC_TEST_OPENCODE_VERIFY_CMD:-opencode \"List connected MCP servers and identify mempalace usage.\"}"
  (cd "$P8_NEG" && eval "$OPENCODE_VERIFY_CMD") >"$OUT8_NEG" 2>&1 || true
  (cd "$P8_POS" && eval "$OPENCODE_VERIFY_CMD") >"$OUT8_POS" 2>&1 || true

  # Patterns can be customized for different opencode outputs.
  POS_PATTERN="${AGENTIC_TEST_OPENCODE_MEMPALACE_POS_PATTERN:-mempalace}"
  NEG_PATTERN="${AGENTIC_TEST_OPENCODE_MEMPALACE_NEG_PATTERN:-mempalace}"

  assert_file_not_contains "$OUT8_NEG" "$NEG_PATTERN"
  assert_file_contains "$OUT8_POS" "$POS_PATTERN"
else
  echo "[e2e] Scenario 8 skipped: requires real 'opencode' binary and working 'python3 -m mempalace'"
fi

echo "[e2e] All scenarios passed"
