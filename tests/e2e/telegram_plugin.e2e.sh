#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
TMP_ROOT="$(mktemp -d /tmp/agentic-telegram-plugin-e2e.XXXXXX)"
trap 'rm -rf "$TMP_ROOT"' EXIT

fail() {
  echo "[telegram-plugin-e2e][FAIL] $1" >&2
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

PROJECT="$TMP_ROOT/project"
HOME_DIR="$TMP_ROOT/home"
mkdir -p "$PROJECT/.opencode" "$HOME_DIR/.config/agentic"
cat > "$HOME_DIR/.config/agentic/opencode-plugins.json" <<'JSON'
{
  "telegram": {"enabled": true, "botToken": "must-not-be-read", "chatId": "must-not-be-read"}
}
JSON

SERVER_LOG="$TMP_ROOT/telegram-server.log"
PORT_FILE="$TMP_ROOT/telegram-port"
python3 - "$SERVER_LOG" "$PORT_FILE" <<'PY' &
import http.server
import socketserver
import sys

log_path, port_path = sys.argv[1:]

class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("content-length", "0"))
        body = self.rfile.read(length).decode(errors="replace")
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(f"{self.path}\n{body}\n")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, *args):
        pass

with socketserver.TCPServer(("127.0.0.1", 0), Handler) as server:
    with open(port_path, "w", encoding="utf-8") as fh:
        fh.write(str(server.server_address[1]))
    server.serve_forever()
PY
SERVER_PID=$!
for _ in 1 2 3 4 5 6 7 8 9 10; do
  [[ -s "$PORT_FILE" ]] && break
  sleep 0.2
done
[[ -s "$PORT_FILE" ]] || fail "fake Telegram server did not start"
trap 'kill "$SERVER_PID" 2>/dev/null || true; rm -rf "$TMP_ROOT"' EXIT
PORT="$(cat "$PORT_FILE")"

NODE_STUB="$TMP_ROOT/telegram-node-stub"
cat > "$NODE_STUB" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
plugin="${1:?missing plugin}"
directory="${2:?missing directory}"
node - "$plugin" "$directory" <<'NODE'
const fs = require("fs")
const vm = require("vm")
const pluginPath = process.argv[2]
const directory = process.argv[3]
let source = fs.readFileSync(pluginPath, "utf8")
source = source.replace(/import type .*\n/g, "")
source = source.replace(/import \{ ([^}]+) \} from "([^"]+)"/g, 'const { $1 } = require("$2")')
source = source.replace(/import (\w+) from "([^"]+)"/g, 'const $1 = require("$2")')
source = source.replace(/type \w+ = \{[\s\S]*?\n\}\n/g, "")
source = source.replace(/export const (\w+): Plugin = async/g, "globalThis.$1 = async")
source = source.replace(/: AgenticPluginConfig/g, "")
source = source.replace(/: string/g, "")
source = source.replace(/: unknown/g, "")
source = source.replace(/ as AgenticPluginConfig/g, "")
source = source.replace(/ as string/g, "")
source = source.replace(/ as any/g, "")
vm.runInNewContext(source, { require, console, process, globalThis, fetch, FormData, Blob })
const client = {
  session: {
    get: async () => ({ data: { title: "hello_world.py", summary: { additions: 1, deletions: 0, files: 1 } } }),
    messages: async () => ({ data: [{ parts: [{ type: "text", text: "created hello_world.py" }] }] }),
  },
}
const dollar = async (strings, ...values) => {
  const line = strings.reduce((acc, item, index) => acc + item + (values[index] ?? ""), "")
  fs.appendFileSync(`${directory}/.opencode/telegram-debug.log`, line + "\n")
}
async function main() {
  const hooks = await globalThis.TelegramNotificationPlugin({ $: dollar, client, directory })
  if (!hooks.event) return
  await hooks.event({ event: { type: "session.idle", properties: { sessionID: "session-secret" } } })
}
main().catch((error) => {
  console.error(error)
  process.exit(1)
})
NODE
EOS
chmod +x "$NODE_STUB"

TOKEN="123456:super-secret-token"
CHAT="987654321"
OUT="$TMP_ROOT/plugin.log"
HOME="$HOME_DIR" \
  OPENCODE_TELEGRAM_BOT_TOKEN="$TOKEN" \
  OPENCODE_TELEGRAM_CHAT_ID="$CHAT" \
  OPENCODE_TELEGRAM_API_BASE_URL="http://127.0.0.1:$PORT" \
  "$NODE_STUB" "$ROOT_DIR/extensions/opencode/plugins/telegram-notification.ts" "$PROJECT" >"$OUT" 2>&1

assert_file_contains "$SERVER_LOG" "/bot$TOKEN/sendMessage"
assert_file_contains "$SERVER_LOG" "$CHAT"
assert_file_contains "$SERVER_LOG" "created hello_world.py"
assert_file_not_contains "$OUT" "$TOKEN"
assert_file_not_contains "$OUT" "$CHAT"
assert_file_not_contains "$HOME_DIR/.config/agentic/opencode-plugins.json" "$TOKEN"
assert_file_not_contains "$HOME_DIR/.config/agentic/opencode-plugins.json" "$CHAT"

echo "telegram plugin e2e ok"
