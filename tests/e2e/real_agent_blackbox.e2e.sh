#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
CLI="${AGENTIC_TEST_CLI:-$ROOT_DIR/agentic}"
TMP_ROOT="$(mktemp -d /tmp/agentic-real-blackbox-e2e.XXXXXX)"
trap 'rm -rf "$TMP_ROOT"' EXIT

fail() {
  echo "[real-blackbox-e2e][FAIL] $1" >&2
  exit 1
}

assert_command() {
  local binary="$1"
  command -v "$binary" >/dev/null 2>&1 || fail "missing required binary: $binary"
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

assert_elapsed_under() {
  local label="$1"
  local elapsed="$2"
  local limit="$3"
  (( elapsed < limit )) || fail "$label took ${elapsed}s, expected under ${limit}s"
}

live_agent_blackbox_enabled() {
  [[ "${AGENTIC_REAL_BLACKBOX_LIVE:-0}" == "1" ]]
}

redact() {
  local text="$1"
  if [[ -n "${OPENCODE_TELEGRAM_BOT_TOKEN:-}" ]]; then
    text="${text//${OPENCODE_TELEGRAM_BOT_TOKEN}/[redacted-token]}"
  fi
  if [[ -n "${OPENCODE_TELEGRAM_CHAT_ID:-}" ]]; then
    text="${text//${OPENCODE_TELEGRAM_CHAT_ID}/[redacted-chat]}"
  fi
  printf '%s\n' "$text"
}

run_install_under_10s() {
  local agent="$1"
  local project="$2"
  local log="$3"
  local started elapsed
  started="$(date +%s)"
  AGENTIC_ENABLE_CONTEXT7=y \
    AGENTIC_ENABLE_MEMPALACE=y \
    AGENTIC_MEMPALACE_SETUP=skip \
    AGENTIC_DOCTOR=0 \
    "$CLI" install \
      --project-dir "$project" \
      --agent-os "$agent" \
      --areas software \
      --specializations software.backend,software.general >"$log" 2>&1
  elapsed=$(( $(date +%s) - started ))
  echo "[real-blackbox-e2e] $agent install elapsed: ${elapsed}s"
  if (( elapsed >= 10 )); then
    cat "$log"
    print_blackbox_evidence "$project"
    fail "$agent install took ${elapsed}s, expected under 10s"
  fi
}

assert_common_install_evidence() {
  local project="$1"
  local agent="$2"
  local agents_file="$3"
  local memory_file="$4"

  [[ -f "$project/.agentic.json" ]] || fail "$agent install did not create .agentic.json"
  [[ -f "$project/$agents_file" ]] || fail "$agent install did not create $agents_file"
  [[ -f "$project/$memory_file" ]] || fail "$agent install did not create $memory_file"
  assert_file_contains "$project/$agents_file" "software/backend"
  assert_file_contains "$project/$agents_file" "software/general"
  assert_file_contains "$project/$agents_file" "Context7"
  assert_file_contains "$project/$memory_file" "MemPalace"
  assert_file_contains "$project/.agentic.json" '"software.backend"'
  assert_file_contains "$project/.agentic.json" '"software.general"'
  assert_file_contains "$project/.agentic.json" '"context7"'
  assert_file_contains "$project/.agentic.json" '"mempalace"'
  assert_file_contains "$project/.agentic.json" '"managed_files"'
}

assert_codex_install_evidence() {
  local project="$1"
  assert_common_install_evidence "$project" "codex" "AGENTS.md" "MEMORY.md"
  assert_file_contains "$project/.codex/config.toml" "[mcp_servers.context7]"
  assert_file_contains "$project/.codex/config.toml" "[mcp_servers.mempalace]"
}

assert_opencode_install_evidence() {
  local project="$1"
  assert_common_install_evidence "$project" "opencode" ".opencode/AGENTS.md" ".opencode/MEMORY.md"
  assert_file_contains "$project/opencode.json" "context7"
  assert_file_contains "$project/opencode.json" "mempalace"
  assert_file_contains "$project/.opencode/opencode.json" "context7"
  assert_file_contains "$project/.opencode/opencode.json" "mempalace"
}

print_blackbox_evidence() {
  local project="$1"
  echo "[real-blackbox-e2e] created files under $project:"
}

run_codex_blackbox() {
  local project="$TMP_ROOT/codex-project"
  local install_log="$TMP_ROOT/codex-install.log"
  local run_log="$TMP_ROOT/codex-run.log"
  run_install_under_10s codex "$project" "$install_log"
  assert_codex_install_evidence "$project"

  if ! live_agent_blackbox_enabled; then
    print_blackbox_evidence "$project"
    echo "[real-blackbox-e2e] codex live run skipped; set AGENTIC_REAL_BLACKBOX_LIVE=1 to execute codex"
    return
  fi

  assert_command codex

  local prompt started elapsed
  prompt="Create a calculator CLI in Python at calculator.py. Then report which Agentic markdown instructions were applied, whether Context7/MemPalace were used, and MemPalace facts read/written."
  started="$(date +%s)"
  if ! codex exec --skip-git-repo-check --ephemeral --sandbox workspace-write -C "$project" "$prompt" </dev/null >"$run_log" 2>&1; then
    cat "$run_log"
    fail "codex blackbox run failed"
  fi
  elapsed=$(( $(date +%s) - started ))
  echo "[real-blackbox-e2e] codex run elapsed: ${elapsed}s"
  assert_elapsed_under "codex run" "$elapsed" 60
  [[ -f "$project/calculator.py" ]] || fail "codex did not create calculator.py"
  print_blackbox_evidence "$project"
  cat "$run_log"
}

run_opencode_blackbox() {
  local project="$TMP_ROOT/opencode-project"
  local install_log="$TMP_ROOT/opencode-install.log"
  local run_log="$TMP_ROOT/opencode-run.log"
  run_install_under_10s opencode "$project" "$install_log"
  assert_opencode_install_evidence "$project"

  if ! live_agent_blackbox_enabled; then
    print_blackbox_evidence "$project"
    echo "[real-blackbox-e2e] opencode live run skipped; set AGENTIC_REAL_BLACKBOX_LIVE=1 to execute opencode"
    return
  fi

  assert_command opencode

  local prompt started elapsed
  prompt="Create a calculator CLI in Python at calculator.py. Then report which Agentic markdown instructions were applied, whether Context7/MemPalace were used, and MemPalace facts read/written."
  started="$(date +%s)"
  if ! opencode run --dir "$project" --dangerously-skip-permissions "$prompt" >"$run_log" 2>&1; then
    cat "$run_log"
    fail "opencode blackbox run failed"
  fi
  elapsed=$(( $(date +%s) - started ))
  echo "[real-blackbox-e2e] opencode run elapsed: ${elapsed}s"
  assert_elapsed_under "opencode run" "$elapsed" 60
  [[ -f "$project/calculator.py" ]] || fail "opencode did not create calculator.py"
  print_blackbox_evidence "$project"
  cat "$run_log"
}

run_opencode_agent_model_mapper_blackbox() {
  local project="$TMP_ROOT/opencode-mapper-project"
  local home="$TMP_ROOT/opencode-mapper-home"
  local install_bin="$TMP_ROOT/opencode-mapper-install-bin"
  local install_log="$TMP_ROOT/opencode-mapper-install.log"
  local run_log="$TMP_ROOT/opencode-mapper-run.log"
  mkdir -p "$home/.config/opencode" "$install_bin"

  cat > "$home/.config/opencode/opencode.json" <<'JSON'
{
  "agent": {
    "developer": {
      "model": "test/provider-main",
      "fallback": ["test/provider-fallback"]
    }
  }
}
JSON
  ln -s "$(command -v python3)" "$install_bin/python3"

  printf '%s\n' "n" "2" "1" "2" "1" "2" "1" "2" "1" "2" "1" "2" "1" "2" "1" "2" "y" "n" "n" | \
    HOME="$home" PATH="$install_bin:/usr/bin:/bin" AGENTIC_FORCE_INTERACTIVE=1 AGENTIC_AGENT_MODEL_MAPPER_NO_FZF=1 AGENTIC_DOCTOR=0 \
      "$CLI" install \
      --project-dir "$project" \
      --agent-os opencode \
      --areas software \
      --specializations software.backend >"$install_log" 2>&1

  assert_file_contains "$install_log" "agent-model-mapper: choose OpenCode models for Agentic roles"
  assert_file_contains "$install_log" "agent-model-mapper: updated .opencode/opencode.json"
  assert_file_contains "$project/.opencode/opencode.json" '"model": "test/provider-main"'
  assert_file_contains "$project/.opencode/opencode.json" '"test/provider-fallback"'
  assert_file_contains "$project/.opencode/opencode.json" '"developer"'
  assert_file_contains "$project/.opencode/opencode.json" '"mode": "subagent"'
  assert_file_contains "$project/.opencode/agent-model-mapper.state.json" '"configured": true'

  if ! live_agent_blackbox_enabled; then
    echo "[real-blackbox-e2e] opencode mapper live run skipped; set AGENTIC_REAL_BLACKBOX_LIVE=1 to execute opencode"
    echo "[real-blackbox-e2e] opencode agent-model-mapper install blackbox ok"
    return
  fi

  assert_command opencode

  if ! python3 - "$project" "$home" "$run_log" <<'PY'
import os
import pty
import select
import subprocess
import sys
import time

project, home, run_log = sys.argv[1:]
env = dict(os.environ)
env.update({
    "HOME": home,
    "OPENCODE_DISABLE_AUTOUPDATE": "1",
})
cmd = [
    "opencode",
    "run",
    "--dir",
    project,
    "--dangerously-skip-permissions",
    "Mapper blackbox: confirm startup is non-blocking, then say mapper complete.",
]
master, slave = pty.openpty()
proc = subprocess.Popen(cmd, stdin=slave, stdout=slave, stderr=slave, env=env)
os.close(slave)

output = []
deadline = time.time() + 30
combined = ""
mapper_skipped = False
while time.time() < deadline:
    ready, _, _ = select.select([master], [], [], 0.1)
    if ready:
        try:
            chunk = os.read(master, 4096)
        except OSError:
            break
        if not chunk:
            break
        text = chunk.decode(errors="replace")
        output.append(text)
        combined += text
        if "agent-model-mapper: skipped because all Agentic roles already have model mappings" in combined:
            mapper_skipped = True
            proc.terminate()
            break
    if proc.poll() is not None:
        break

if mapper_skipped:
    time.sleep(0.2)
    if proc.poll() is None:
        proc.kill()
elif proc.poll() is None:
    with open(run_log, "w", encoding="utf-8") as fh:
        fh.write("".join(output))
    proc.terminate()
    time.sleep(1)
    if proc.poll() is None:
        proc.kill()
    raise SystemExit("opencode mapper non-blocking blackbox timed out")

while True:
    ready, _, _ = select.select([master], [], [], 0)
    if not ready:
        break
    try:
        chunk = os.read(master, 4096)
    except OSError:
        break
    if not chunk:
        break
    output.append(chunk.decode(errors="replace"))

with open(run_log, "w", encoding="utf-8") as fh:
    fh.write("".join(output))
if proc.returncode not in (0, -15, 143):
    raise SystemExit(proc.returncode)
if "Select main model" in combined or "Select fallback model" in combined:
    raise SystemExit("runtime agent-model-mapper prompt was observed")
if not mapper_skipped:
    raise SystemExit("runtime agent-model-mapper skip marker was not observed")
PY
  then
    [[ -f "$run_log" ]] && cat "$run_log"
    fail "opencode agent-model-mapper blackbox failed"
  fi

  assert_file_contains "$run_log" "agent-model-mapper: skipped because all Agentic roles already have model mappings"
  assert_file_not_contains "$run_log" "Select main model"
  assert_file_not_contains "$run_log" "Select fallback model"
  assert_file_not_contains "$run_log" "Write .opencode/opencode.json agent model mapping?"

  if grep -Eq '([0-9]+;){3,}[0-9]+[mM]' "$run_log"; then
    fail "mapper prompt received terminal mouse/control escape sequence input"
  fi

  echo "[real-blackbox-e2e] opencode agent-model-mapper blackbox ok"
}

run_telegram_blackbox() {
  local project="$TMP_ROOT/telegram-project"
  local home="$TMP_ROOT/telegram-home"
  local install_log="$TMP_ROOT/telegram-install.log"
  local run_log="$TMP_ROOT/telegram-run.log"
  mkdir -p "$home/.config/agentic"
  cat > "$home/.config/agentic/opencode-plugins.json" <<'JSON'
{
  "telegram": {"enabled": true},
  "agentModelMapper": {"enabled": false}
}
JSON

  HOME="$home" AGENTIC_ENABLE_CONTEXT7=n AGENTIC_ENABLE_MEMPALACE=n AGENTIC_DOCTOR=0 \
    "$CLI" install \
      --project-dir "$project" \
      --agent-os opencode \
      --areas software \
      --specializations software.backend >"$install_log" 2>&1

  assert_file_contains "$project/.opencode/plugins/telegram-notification.ts" "Generated by agentic"
  assert_file_contains "$project/.opencode/opencode.json" "telegram-notification"
  assert_file_contains "$project/.agentic.json" "telegram-notification"

  if ! live_agent_blackbox_enabled; then
    echo "[real-blackbox-e2e] Telegram live run skipped; set AGENTIC_REAL_BLACKBOX_LIVE=1 to execute opencode and send a message"
    return
  fi

  [[ -n "${OPENCODE_TELEGRAM_BOT_TOKEN:-}" ]] || fail "OPENCODE_TELEGRAM_BOT_TOKEN is required"
  [[ -n "${OPENCODE_TELEGRAM_CHAT_ID:-}" ]] || fail "OPENCODE_TELEGRAM_CHAT_ID is required"
  assert_command opencode

  if ! HOME="$home" opencode run --dir "$project" --dangerously-skip-permissions "Create hello_world.py that prints hello world" >"$run_log" 2>&1; then
    redact "$(cat "$run_log")"
    fail "opencode Telegram blackbox run failed"
  fi
  [[ -f "$project/hello_world.py" ]] || fail "opencode did not create hello_world.py"

  echo "[real-blackbox-e2e] Telegram run log (redacted):"
  redact "$(cat "$run_log")"
  echo "[real-blackbox-e2e] Telegram message evidence: OpenCode run completed with telegram-notification enabled; verify chat for a new hello_world.py session notification."
}

selected_blackbox="${AGENTIC_REAL_BLACKBOX_ONLY:-all}"

case "$selected_blackbox" in
  codex)
    run_codex_blackbox
    ;;
  opencode)
    run_opencode_blackbox
    ;;
  opencode-mapper)
    run_opencode_agent_model_mapper_blackbox
    ;;
  telegram)
    run_telegram_blackbox
    ;;
  all)
    run_codex_blackbox
    run_opencode_blackbox
    run_opencode_agent_model_mapper_blackbox
    run_telegram_blackbox
    ;;
  *)
    fail "unknown AGENTIC_REAL_BLACKBOX_ONLY value: ${AGENTIC_REAL_BLACKBOX_ONLY:-}"
    ;;
esac

echo "real agent blackbox e2e ok: $selected_blackbox"
