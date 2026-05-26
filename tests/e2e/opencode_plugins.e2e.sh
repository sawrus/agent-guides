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
mkdir -p "$PROJECT/.opencode/plugins"
cp "$ROOT_DIR/extensions/opencode/plugins/agent-model-mapper.ts" "$PROJECT/.opencode/plugins/agent-model-mapper.ts"

assert_not_exists "$ROOT_DIR/extensions/opencode/plugins/model-checker.ts"
assert_not_exists "$ROOT_DIR/extensions/opencode/plugins/model-checker.json"
assert_file_contains "$ROOT_DIR/extensions/opencode/opencode.json" "agent-model-mapper"
assert_file_contains "$ROOT_DIR/extensions/opencode/opencode.json" "instruction_reviewer"
assert_file_contains "$ROOT_DIR/extensions/opencode/opencode.json" "memory_curator"
assert_file_not_contains "$ROOT_DIR/extensions/opencode/opencode.json" "model-checker"

NODE_STUB="$TMP_ROOT/node-stub"
cat > "$NODE_STUB" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
mode="${1:?missing mode}"
plugin="${2:?missing plugin}"
directory="${3:?missing directory}"
node - "$mode" "$plugin" "$directory" <<'NODE'
const fs = require("fs")
const path = require("path")
const vm = require("vm")

const mode = process.argv[2]
const pluginPath = process.argv[3]
const directory = process.argv[4]
let source = fs.readFileSync(pluginPath, "utf8")
source = source.replace(/import type .*\n/g, "")
source = source.replace(/import \{ ([^}]+) \} from "([^"]+)"/g, 'const { $1 } = require("$2")')
source = source.replace(/import (\w+) from "([^"]+)"/g, 'const $1 = require("$2")')
source = source.replace(/export const (\w+): Plugin = async/g, "globalThis.$1 = async")
source = source.replace(/const rl = readline\.createInterface\(\{ input: process\.stdin, output: process\.stdout \}\)/, 'const rl = globalThis.AGENTIC_TEST_RL || readline.createInterface({ input: process.stdin, output: process.stdout })')
source = source.replace(/rl\.close\(\)/g, 'if (!globalThis.AGENTIC_TEST_RL) rl.close()')
source = source.replace(/type \w+ = \{[\s\S]*?\n\}\n/g, "")
source = source.replace(/: Promise<[^>]+>/g, "")
source = source.replace(/: AgenticPluginConfig/g, "")
source = source.replace(/: boolean/g, "")
source = source.replace(/: Record<string, any> \| undefined/g, "")
source = source.replace(/: Record<string, \{ model: string; fallback: string\[\] \}>/g, "")
source = source.replace(/: Record<string, any>/g, "")
source = source.replace(/: Record<string, string>/g, "")
source = source.replace(/: readline\.Interface/g, "")
source = source.replace(/: string \| undefined/g, "")
source = source.replace(/: "main" \| "fallback"/g, "")
source = source.replace(/: unknown/g, "")
source = source.replace(/: string\[\]/g, "")
source = source.replace(/: string/g, "")
source = source.replace(/: Role\[\]/g, "")
source = source.replace(/: Role/g, "")
source = source.replace(/ as Record<string, unknown>/g, "")
source = source.replace(/ as Record<string, any> \| undefined/g, "")
source = source.replace(/ as Record<string, any>/g, "")
source = source.replace(/ as AgenticPluginConfig/g, "")
source = source.replace(/ as string/g, "")
vm.runInNewContext(source, { require, console, process, globalThis })

async function main() {
  if (mode === "mapper-tty") {
    Object.defineProperty(process.stdin, "isTTY", { value: true })
    Object.defineProperty(process.stdout, "isTTY", { value: true })
    const answers = process.env.AGENTIC_AGENT_MODEL_MAPPER_ALLOW_FZF
      ? ["y"]
      : ["1", "2", "1", "2", "1", "2", "1", "2", "1", "2", "1", "2", "1", "2", "1", "2", "1", "2", "y"]
    if (!process.env.AGENTIC_AGENT_MODEL_MAPPER_ALLOW_FZF) {
      process.env.AGENTIC_AGENT_MODEL_MAPPER_NO_FZF = "1"
    }
    globalThis.AGENTIC_TEST_RL = {
      question: async (prompt) => {
        process.stdout.write(prompt)
        return answers.shift() || "1"
      },
      close: () => {},
    }
  }
  if (mode === "mapper" || mode === "mapper-tty") {
    await globalThis.AgentModelMapperPlugin({ directory })
  }
}
main().catch((error) => {
  console.error(error)
  process.exit(1)
})
NODE
EOS
chmod +x "$NODE_STUB"

HOME_NONTTY="$TMP_ROOT/home-nontty"
XDG_CONFIG_NONTTY="$TMP_ROOT/xdg-config-nontty"
XDG_DATA_NONTTY="$TMP_ROOT/xdg-data-nontty"
mkdir -p "$XDG_CONFIG_NONTTY/agentic" "$HOME_NONTTY/.config/opencode"
cat > "$XDG_CONFIG_NONTTY/agentic/opencode-plugins.json" <<'JSON'
{
  "agentModelMapper": {"enabled": true}
}
JSON
cat > "$HOME_NONTTY/.config/opencode/opencode.json" <<'JSON'
{
  "agent": {
    "developer": {
      "model": "local/user-main",
      "fallback": ["local/user-fallback"]
    }
  }
}
JSON
BEFORE_HASH="$(shasum -a 256 "$PROJECT/.opencode/opencode.json" | cut -d ' ' -f 1)"
OUT_NONTTY="$TMP_ROOT/mapper-nontty.log"
HOME="$HOME_NONTTY" XDG_CONFIG_HOME="$XDG_CONFIG_NONTTY" XDG_DATA_HOME="$XDG_DATA_NONTTY" "$NODE_STUB" mapper "$PROJECT/.opencode/plugins/agent-model-mapper.ts" "$PROJECT" >"$OUT_NONTTY" 2>&1 || {
  cat "$OUT_NONTTY" >&2
  exit 1
}
AFTER_HASH="$(shasum -a 256 "$PROJECT/.opencode/opencode.json" | cut -d ' ' -f 1)"
[[ "$BEFORE_HASH" == "$AFTER_HASH" ]] || fail "non-TTY mapper changed opencode.json"
assert_file_contains "$OUT_NONTTY" "install-time model mapping is required"
assert_file_not_contains "$OUT_NONTTY" "Select main model"
assert_file_not_contains "$OUT_NONTTY" "Select fallback model"

cat > "$PROJECT/.opencode/agent-model-mapper.state.json" <<'JSON'
{
  "configured": true,
  "roles": ["designer", "developer", "devops-engineer", "instruction_reviewer", "memory_curator", "pm", "product-owner", "qa", "team-lead"]
}
JSON
OUT_TTY_SECOND="$TMP_ROOT/mapper-tty-second.log"
HOME="$HOME_NONTTY" XDG_CONFIG_HOME="$XDG_CONFIG_NONTTY" XDG_DATA_HOME="$XDG_DATA_NONTTY" "$NODE_STUB" mapper-tty "$PROJECT/.opencode/plugins/agent-model-mapper.ts" "$PROJECT" >"$OUT_TTY_SECOND" 2>&1
assert_file_contains "$OUT_TTY_SECOND" "skipped because all Agentic roles already have model mappings"

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
