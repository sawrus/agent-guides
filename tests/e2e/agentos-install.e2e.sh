#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INSTALLER="$ROOT_DIR/agentos-install.sh"
TMP_ROOT="$(mktemp -d /tmp/agentos-install-e2e.XXXXXX)"
export XDG_CONFIG_HOME="$TMP_ROOT/xdg-config"
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

echo "[e2e] Scenario 0: no args in non-interactive mode -> usage + exit 1"
OUT0="$TMP_ROOT/no-args-noninteractive.log"
set +e
"$INSTALLER" >"$OUT0" 2>&1
STATUS0=$?
set -e
[[ "$STATUS0" -eq 1 ]] || fail "Expected exit code 1 for no-args non-interactive, got $STATUS0"
assert_file_contains "$OUT0" "AgentOS Installer"
assert_file_contains "$OUT0" "Usage:"

echo "[e2e] Scenario 1: legacy CLI install (single agent-os)"
P1="$TMP_ROOT/project-opencode"
"$INSTALLER" install \
  --project-dir "$P1" \
  --agent-os opencode \
  --areas software \
  --specializations software.backend \
  --theme light

assert_exists "$P1/.opencode"
assert_exists "$P1/.agent/rules"
assert_exists "$P1/.agent/skills"
assert_exists "$P1/.agent/workflows"
assert_exists "$P1/AGENTS.md"
assert_file_contains "$P1/AGENTS.md" "software/backend"
assert_file_contains "$P1/AGENTS.md" "Dynamic loading of guidance"
assert_file_contains "$XDG_CONFIG_HOME/agentos-installer/theme" "light"

echo "[e2e] Scenario 2: CLI install with multi-agent CSV"
P2="$TMP_ROOT/project-multi-agent"
"$INSTALLER" install \
  --project-dir "$P2" \
  --agent-os codex,claude \
  --areas software \
  --specializations software.frontend

assert_exists "$P2/.codex"
assert_exists "$P2/.claude"
assert_exists "$P2/.agent/rules"
assert_exists "$P2/.agent/skills"
assert_exists "$P2/.agent/workflows"
assert_exists "$P2/AGENTS.md"
assert_file_contains "$P2/AGENTS.md" "software/frontend"


echo "[e2e] Scenario 3: no-args interactive path -> TUI fallback (no fzf, user declines install)"
P3="$TMP_ROOT/project-no-args-tui"
OUT3="$TMP_ROOT/no-args-tui.log"
NO_FZF_PATH="$TMP_ROOT/no-fzf-bin"
mkdir -p "$NO_FZF_PATH"

# Input order:
# 1) auto-install fzf confirmation
# 2) project dir
# 3) agent-os multi indexes
# 4) areas indexes
# 5) specs indexes
printf '%s\n' "n" "$P3" "1,2" "2" "1,3" | \
  env AGENTOS_FORCE_INTERACTIVE=1 PATH="$NO_FZF_PATH:/usr/bin:/bin" \
  "$INSTALLER" >"$OUT3" 2>&1

assert_exists "$P3/.opencode"
assert_exists "$P3/.agent/rules"
assert_exists "$P3/.agent/skills"
assert_exists "$P3/.agent/workflows"
assert_exists "$P3/AGENTS.md"
assert_file_contains "$P3/AGENTS.md" "software/backend"
assert_file_contains "$P3/AGENTS.md" "software/frontend"
assert_file_contains "$OUT3" "User declined automatic fzf installation"
if grep -Fq "Select interface theme:" "$OUT3"; then
  fail "Theme picker should be skipped when a saved theme exists"
fi


echo "[e2e] Scenario 4: fzf missing -> auto-install success path (Windows/Git Bash simulation)"
P4="$TMP_ROOT/project-auto-fzf"
OUT4="$TMP_ROOT/tui-auto-fzf.log"
FAKE_AUTO_BIN="$TMP_ROOT/fake-auto-bin"
mkdir -p "$FAKE_AUTO_BIN"

cat > "$FAKE_AUTO_BIN/scoop" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
BIN_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ "${1:-}" == "install" ]] && [[ "${2:-}" == "fzf" ]]; then
  cat > "$BIN_DIR/fzf" <<'EOT'
#!/usr/bin/env bash
set -euo pipefail
prompt=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prompt)
      prompt="${2:-}"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
case "$prompt" in
  "Select Agent OS target(s): ")
    printf '%s\n' "codex" "claude"
    ;;
  "Select area(s): ")
    printf '%s\n' "software"
    ;;
  "Select specialization(s) for 'software': ")
    printf '%s\n' "backend" "frontend"
    ;;
  *)
    exit 0
    ;;
esac
EOT
  chmod +x "$BIN_DIR/fzf"
  exit 0
fi
exit 1
EOS
chmod +x "$FAKE_AUTO_BIN/scoop"

# Input order:
# 1) auto-install fzf confirmation
# 2) project dir
printf '%s\n' "y" "$P4" | \
  env AGENTOS_FORCE_INTERACTIVE=1 AGENTOS_PLATFORM_OVERRIDE=windows PATH="$FAKE_AUTO_BIN:/usr/bin:/bin" \
  "$INSTALLER" tui --theme dark >"$OUT4" 2>&1

assert_exists "$P4/.codex"
assert_exists "$P4/.claude"
assert_exists "$P4/.agent/rules"
assert_exists "$P4/.agent/skills"
assert_exists "$P4/.agent/workflows"
assert_exists "$P4/AGENTS.md"
assert_file_contains "$OUT4" "fzf installed successfully"
if grep -Fq "Select interface theme:" "$OUT4"; then
  fail "Theme picker should be skipped when --theme is provided"
fi

echo "[e2e] Scenario 5: self-install dry-run + overwrite behavior"
SELF_BIN="$TMP_ROOT/self/bin"
OUT5A="$TMP_ROOT/self-install-dry.log"
OUT5B="$TMP_ROOT/self-install-real.log"
OUT5C="$TMP_ROOT/self-install-no-force.log"
OUT5D="$TMP_ROOT/self-install-force.log"

"$INSTALLER" self-install --bin-dir "$SELF_BIN" --dry-run >"$OUT5A" 2>&1
assert_not_exists "$SELF_BIN/agentos-install"
assert_file_contains "$OUT5A" "PATH does not include"

"$INSTALLER" self-install --bin-dir "$SELF_BIN" >"$OUT5B" 2>&1
assert_exists "$SELF_BIN/agentos-install"
assert_executable "$SELF_BIN/agentos-install"

set +e
"$INSTALLER" self-install --bin-dir "$SELF_BIN" >"$OUT5C" 2>&1
STATUS5C=$?
set -e
[[ "$STATUS5C" -ne 0 ]] || fail "Expected self-install without --force to fail on existing target"
assert_file_contains "$OUT5C" "Use --force to overwrite"

"$INSTALLER" self-install --bin-dir "$SELF_BIN" --force >"$OUT5D" 2>&1
assert_file_contains "$OUT5D" "Installed:"

echo "[e2e] All scenarios passed"
