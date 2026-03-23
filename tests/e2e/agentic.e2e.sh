#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
CLI="$ROOT_DIR/agentic"
TMP_ROOT="$(mktemp -d /tmp/agentic-e2e.XXXXXX)"
trap 'rm -rf "$TMP_ROOT"' EXIT

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
  grep -Fq "$needle" "$path" || fail "Expected '$needle' in $path"
}

assert_output_contains() {
  local output="$1"
  local needle="$2"
  grep -Fq "$needle" <<< "$output" || fail "Expected '$needle' in output"
}

assert_output_not_contains() {
  local output="$1"
  local needle="$2"
  if grep -Fq "$needle" <<< "$output"; then
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
    exit 0
  fi
fi

exit 1
EOS
chmod +x "$FAKE_GIT_BIN/git"

echo "[e2e] Scenario 0: no args in non-interactive mode -> usage + exit 1"
OUT0="$TMP_ROOT/no-args-noninteractive.log"
set +e
"$CLI" >"$OUT0" 2>&1
STATUS0=$?
set -e
[[ "$STATUS0" -eq 1 ]] || fail "Expected exit code 1 for no-args non-interactive, got $STATUS0"
assert_file_contains "$OUT0" "Agentic Installer"
assert_file_contains "$OUT0" "Usage:"

echo "[e2e] Scenario 1: dev mode install from repository checkout"
P1="$TMP_ROOT/project-dev-install"
"$CLI" install \
  --project-dir "$P1" \
  --agent-os opencode \
  --areas software \
  --specializations software.backend \
  --theme light

assert_exists "$P1/.opencode"
assert_exists "$P1/.agent/rules"
assert_exists "$P1/.agent/skills"
assert_exists "$P1/.agent/workflows"
assert_exists "$P1/.agent/prompts"
assert_exists "$P1/AGENTS.md"
assert_file_contains "$P1/AGENTS.md" "software/backend"
assert_file_contains "$P1/AGENTS.md" "Dynamic loading of guidance"

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
HOME="$HOME_INSTALLED" PATH="$FAKE_GIT_BIN:/usr/bin:/bin" AGENTIC_TEST_GIT_LOG="$GIT_LOG" "$INSTALLED_BIN" upgrade >"$OUT4" 2>&1
assert_file_contains "$GIT_LOG" "git -C $HOME_INSTALLED/.local/share/agentic/repo pull --ff-only"
assert_exists "$HOME_INSTALLED/.local/share/agentic/repo/.last-pull"

echo "[e2e] Scenario 5: TUI stores theme config and reuses it"
HOME_TUI="$TMP_ROOT/home-tui"
OUT5A="$TMP_ROOT/tui-save-theme.log"
OUT5B="$TMP_ROOT/tui-reuse-theme.log"
NO_FZF_PATH="$TMP_ROOT/no-fzf-bin"
mkdir -p "$NO_FZF_PATH"
P5A="$TMP_ROOT/project-tui-a"
P5B="$TMP_ROOT/project-tui-b"

printf '%s\n' "3" "n" "$P5A" "1" "1" "1" | \
  env HOME="$HOME_TUI" AGENTIC_FORCE_INTERACTIVE=1 PATH="$FAKE_GIT_BIN:$NO_FZF_PATH:/usr/bin:/bin" AGENTIC_TEST_GIT_LOG="$GIT_LOG" \
  "$INSTALLED_BIN" tui >"$OUT5A" 2>&1

assert_exists "$HOME_TUI/.config/agentic/config"
assert_file_contains "$HOME_TUI/.config/agentic/config" "theme=light"
assert_exists "$HOME_TUI/.local/share/agentic/repo/areas/software/frontend"
assert_exists "$P5A/.agent/rules"
assert_file_contains "$OUT5A" "Theme: light"

printf '%s\n' "n" "$P5B" "1" "1" "1" | \
  env HOME="$HOME_TUI" AGENTIC_FORCE_INTERACTIVE=1 PATH="$FAKE_GIT_BIN:$NO_FZF_PATH:/usr/bin:/bin" AGENTIC_TEST_GIT_LOG="$GIT_LOG" \
  "$INSTALLED_BIN" tui >"$OUT5B" 2>&1

assert_exists "$P5B/.agent/rules"
assert_file_contains "$OUT5B" "Theme: light"
assert_output_not_contains "$(cat "$OUT5B")" "Select interface theme:"

echo "[e2e] All scenarios passed"
