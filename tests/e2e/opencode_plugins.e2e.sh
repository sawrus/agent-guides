#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
TMP_ROOT="$(mktemp -d /tmp/agentic-opencode-plugins-e2e.XXXXXX)"
trap 'rm -rf "$TMP_ROOT"' EXIT

fail() {
  echo "[opencode-plugins-e2e][FAIL] $1" >&2
  exit 1
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

assert_exists() {
  local path="$1"
  [[ -e "$path" ]] || fail "Expected path to exist: $path"
}

assert_not_exists() {
  local path="$1"
  [[ ! -e "$path" ]] || fail "Expected path to not exist: $path"
}

PROJECT="$TMP_ROOT/project"
mkdir -p "$PROJECT/.opencode"
cp -R "$ROOT_DIR/extensions/opencode/agents" "$PROJECT/.opencode/agents"
cp "$ROOT_DIR/extensions/opencode/opencode.json" "$PROJECT/.opencode/opencode.json"

assert_not_exists "$ROOT_DIR/extensions/opencode/plugins/agent-model-mapper.ts"
assert_not_exists "$ROOT_DIR/extensions/opencode/plugins/model-checker.ts"
assert_not_exists "$ROOT_DIR/extensions/opencode/plugins/model-checker.json"
assert_file_not_contains "$ROOT_DIR/extensions/opencode/opencode.json" "agent-model-mapper"
assert_file_contains "$ROOT_DIR/extensions/opencode/opencode.json" "instruction_reviewer"
assert_file_contains "$ROOT_DIR/extensions/opencode/opencode.json" "memory_curator"
assert_file_not_contains "$ROOT_DIR/extensions/opencode/opencode.json" "model-checker"

INSTALL_PROJECT="$TMP_ROOT/install-project"
INSTALL_HOME="$TMP_ROOT/install-home"
INSTALL_XDG_CONFIG_HOME="$TMP_ROOT/install-xdg-config"
INSTALL_BIN="$TMP_ROOT/install-bin"
INSTALL_LOG="$TMP_ROOT/install-mapper.log"
PYTHON3_BIN="$(command -v python3)"
mkdir -p "$INSTALL_HOME/.config/opencode" "$INSTALL_HOME/.local/share/opencode" "$INSTALL_HOME/.cache/opencode" "$INSTALL_BIN"
ln -s "$PYTHON3_BIN" "$INSTALL_BIN/python3"
cat > "$INSTALL_HOME/.config/opencode/opencode.json" <<'JSON'
{
  "agent": {
    "developer": {
      "model": "local/install-main",
      "fallback": ["local/install-fallback"]
    }
  }
}
JSON
cat > "$INSTALL_HOME/.local/share/opencode/auth.json" <<'JSON'
{
  "github-copilot": {"type": "oauth", "access": "redacted"}
}
JSON
cat > "$INSTALL_HOME/.cache/opencode/models.json" <<'JSON'
{
  "github-copilot": {
    "models": {
      "claude-opus-4.6": {"id": "claude-opus-4.6", "status": "stable"},
      "gpt-5.5": {"id": "gpt-5.5"},
      "old-model": {"id": "old-model", "deprecated": true}
    }
  }
}
JSON
printf '%s\n' "n" "2" "1" "2" "1" "2" "1" "2" "1" "2" "1" "2" "1" "2" "1" "2" "1" "2" "1" "2" "y" "n" "n" | \
  env HOME="$INSTALL_HOME" XDG_CONFIG_HOME="$INSTALL_XDG_CONFIG_HOME" PATH="$INSTALL_BIN:/usr/bin:/bin" AGENTIC_FORCE_INTERACTIVE=1 AGENTIC_AGENT_MODEL_MAPPER_NO_FZF=1 AGENTIC_DOCTOR=0 "$ROOT_DIR/agentic" install \
    --project-dir "$INSTALL_PROJECT" \
    --agent-os opencode \
    --areas software \
    --specializations software.backend \
    --theme=light >"$INSTALL_LOG" 2>&1
assert_file_contains "$INSTALL_LOG" "agent-model-mapper: choose OpenCode models for Agentic roles"
assert_file_contains "$INSTALL_LOG" "agent-model-mapper: updated .opencode/opencode.json"
assert_file_contains "$INSTALL_LOG" "github-copilot/claude-opus-4.6"
assert_file_contains "$INSTALL_LOG" "github-copilot/gpt-5.5"
assert_file_not_contains "$INSTALL_LOG" "github-copilot/old-model"
assert_exists "$INSTALL_PROJECT/.opencode/agent-model-mapper.state.json"
assert_file_contains "$INSTALL_PROJECT/.opencode/opencode.json" '"model": "local/install-main"'
assert_file_contains "$INSTALL_PROJECT/.opencode/opencode.json" '"local/install-fallback"'
assert_file_contains "$INSTALL_PROJECT/.opencode/opencode.json" '"instruction_reviewer"'
assert_file_contains "$INSTALL_PROJECT/.opencode/opencode.json" '"memory_curator"'

TELEGRAM_PLUGIN="$ROOT_DIR/extensions/opencode/plugins/telegram-notification.ts"
assert_file_contains "$TELEGRAM_PLUGIN" ".agentic.json"
assert_file_not_contains "$TELEGRAM_PLUGIN" "parse_mode"
assert_file_not_contains "$TELEGRAM_PLUGIN" "MarkdownV2"
assert_file_not_contains "$TELEGRAM_PLUGIN" "process.env.OPENCODE_TELEGRAM_BOT_TOKEN"
assert_file_not_contains "$TELEGRAM_PLUGIN" "process.env.OPENCODE_TELEGRAM_CHAT_ID"
assert_file_contains "$TELEGRAM_PLUGIN" "text: textToSend.slice(0, 4096)"
assert_file_contains "$TELEGRAM_PLUGIN" "[redacted]"

echo "opencode plugins e2e ok"
