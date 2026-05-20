#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
CLI="${AGENTIC_TEST_CLI:-$ROOT_DIR/agentic}"
TMP_ROOT="$(mktemp -d /tmp/agentic-doctor-e2e.XXXXXX)"
trap 'rm -rf "$TMP_ROOT"' EXIT

fail() {
  echo "[doctor-e2e][FAIL] $1" >&2
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

assert_file_matches() {
  local path="$1"
  local pattern="$2"
  grep -Eq -- "$pattern" "$path" || fail "Expected pattern '$pattern' in $path"
}

assert_exists() {
  local path="$1"
  [[ -e "$path" ]] || fail "Expected path to exist: $path"
}

FAKE_BIN="$TMP_ROOT/fake-bin"
mkdir -p "$FAKE_BIN"

cat > "$FAKE_BIN/codex" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
work_dir=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -C)
      work_dir="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
mkdir -p "$work_dir/src"
echo "codex doctor touched" > "$work_dir/src/doctor-touched.txt"
echo "codex ok"
EOS

cat > "$FAKE_BIN/opencode" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
printf 'opencode args: %s\n' "$*"
work_dir=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir)
      work_dir="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done
mkdir -p "$work_dir/src"
echo "opencode doctor touched" > "$work_dir/src/doctor-touched.txt"
echo '{"type":"message","text":"opencode ok"}'
EOS

cat > "$FAKE_BIN/claude" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
mkdir -p src
echo "claude doctor touched" > src/doctor-touched.txt
echo '{"type":"result","result":"claude ok"}'
EOS

cat > "$FAKE_BIN/gemini" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${AGENTIC_FAKE_FAIL_GEMINI:-}" == "1" ]]; then
  echo "SyntaxError: Invalid regular expression flags" >&2
  exit 7
fi
mkdir -p src
echo "gemini doctor touched" > src/doctor-touched.txt
echo "gemini ok"
EOS

cat > "$FAKE_BIN/pip" <<'EOS'
#!/usr/bin/env bash
exit 0
EOS

cat > "$FAKE_BIN/mempalace" <<'EOS'
#!/usr/bin/env bash
exit 0
EOS

cat > "$FAKE_BIN/mempalace-mcp" <<'EOS'
#!/usr/bin/env bash
exit 0
EOS

chmod +x "$FAKE_BIN"/*

echo "[doctor-e2e] Scenario 1: selected codex,opencode runs exactly two doctor checks"
P1="$TMP_ROOT/project-codex-opencode"
OUT1="$TMP_ROOT/codex-opencode.log"
HOME1="$TMP_ROOT/home-1"
PATH="$FAKE_BIN:/usr/bin:/bin" \
  HOME="$HOME1" \
  TMPDIR="$TMP_ROOT" \
  AGENTIC_ENABLE_CONTEXT7=n \
  AGENTIC_ENABLE_MEMPALACE=y \
  "$CLI" install \
    --project-dir "$P1" \
    --agent-os codex,opencode \
    --areas software \
    --specializations software.backend,software.general >"$OUT1" 2>&1

assert_file_contains "$OUT1" "=== Agentic doctor ==="
assert_file_contains "$OUT1" "Doctor timeout: 10s per agent"
assert_file_contains "$OUT1" "✅ codex: /develop-feature smoke passed"
assert_file_contains "$OUT1" "✅ opencode: lightweight smoke passed"
assert_file_matches "$OUT1" "codex doctor finished: timeout=10s exit=0 elapsed=[0-9]+s"
assert_file_matches "$OUT1" "opencode doctor finished: timeout=10s exit=0 elapsed=[0-9]+s"
if grep -Fq "claude:" "$OUT1" || grep -Fq "gemini:" "$OUT1"; then
  fail "Doctor ran unselected agentos"
fi
if [[ "$(grep -Ec '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} (✅|❌) (codex|opencode|claude|gemini):|^(✅|❌) (codex|opencode|claude|gemini):' "$OUT1")" -ne 2 ]]; then
  fail "Expected exactly two doctor rows"
fi
grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} .*Agentic doctor' "$OUT1" || fail "Expected timestamped doctor output"

LOG1="$(sed -n 's/^.*Agentic log file: //p' "$OUT1" | tail -1 | tr -d "'")"
assert_exists "$LOG1"
assert_file_contains "$LOG1" "=== Agentic doctor ==="
assert_file_contains "$LOG1" "codex ok"
assert_file_contains "$LOG1" "opencode ok"
assert_file_contains "$LOG1" "opencode args: run --pure --dir"
assert_file_contains "$LOG1" "--log-level ERROR Reply with exactly: AGENTIC_DOCTOR_OK"
assert_file_not_contains "$LOG1" "--command develop-feature"

assert_file_not_contains "$P1/.codex/config.toml" "args ="
assert_file_contains "$P1/.codex/config.toml" 'command = "mempalace-mcp"'
python3 - "$P1/opencode.json" "$P1/.opencode/opencode.json" <<'PY'
import json
import sys
for raw in sys.argv[1:]:
    with open(raw, encoding="utf-8") as fh:
        data = json.load(fh)
    command = data["mcp"]["mempalace"]["command"]
    if command != ["mempalace-mcp"]:
        raise SystemExit(f"unexpected mempalace command in {raw}: {command!r}")
PY

if [[ -e "$P1/src/doctor-touched.txt" ]]; then
  fail "Doctor wrote into the target project"
fi

echo "[doctor-e2e] Scenario 2: selected claude,gemini reports failing gemini without failing install"
P2="$TMP_ROOT/project-claude-gemini"
OUT2="$TMP_ROOT/claude-gemini.log"
HOME2="$TMP_ROOT/home-2"
PATH="$FAKE_BIN:/usr/bin:/bin" \
  HOME="$HOME2" \
  TMPDIR="$TMP_ROOT" \
  AGENTIC_ENABLE_CONTEXT7=n \
  AGENTIC_ENABLE_MEMPALACE=n \
  AGENTIC_FAKE_FAIL_GEMINI=1 \
  "$CLI" install \
    --project-dir "$P2" \
    --agent-os claude,gemini \
    --areas software \
    --specializations software.backend >"$OUT2" 2>&1

assert_file_contains "$OUT2" "✅ claude: /develop-feature smoke passed"
assert_file_contains "$OUT2" "❌ gemini: /develop-feature smoke failed"
assert_file_contains "$OUT2" "Agentic doctor completed with 1 failing check(s)"
if [[ -e "$P2/src/doctor-touched.txt" ]]; then
  fail "Doctor wrote into the second target project"
fi

echo "[doctor-e2e] Scenario 3: AGENTIC_DOCTOR=0 skips doctor"
P3="$TMP_ROOT/project-skip"
OUT3="$TMP_ROOT/skip.log"
HOME3="$TMP_ROOT/home-3"
PATH="$FAKE_BIN:/usr/bin:/bin" \
  HOME="$HOME3" \
  TMPDIR="$TMP_ROOT" \
  AGENTIC_DOCTOR=0 \
  AGENTIC_ENABLE_CONTEXT7=n \
  AGENTIC_ENABLE_MEMPALACE=n \
  "$CLI" install \
    --project-dir "$P3" \
    --agent-os codex,opencode \
    --areas software \
    --specializations software.backend >"$OUT3" 2>&1

assert_file_contains "$OUT3" "Agentic doctor skipped"
if grep -Fq "✅ codex" "$OUT3"; then
  fail "Doctor ran while disabled"
fi

echo "[doctor-e2e] Scenario 4: hung codex times out and opencode still runs"
cat > "$FAKE_BIN/codex" <<'EOS'
#!/usr/bin/env bash
sleep 30
EOS
chmod +x "$FAKE_BIN/codex"
P4="$TMP_ROOT/project-timeout-continuation"
OUT4="$TMP_ROOT/timeout-continuation.log"
HOME4="$TMP_ROOT/home-4"
PATH="$FAKE_BIN:/usr/bin:/bin" \
  HOME="$HOME4" \
  TMPDIR="$TMP_ROOT" \
  AGENTIC_ENABLE_CONTEXT7=n \
  AGENTIC_ENABLE_MEMPALACE=n \
  AGENTIC_DOCTOR_TIMEOUT_SECONDS=1 \
  "$CLI" install \
    --project-dir "$P4" \
    --agent-os codex,opencode \
    --areas software \
    --specializations software.backend >"$OUT4" 2>&1

assert_file_contains "$OUT4" "Doctor timeout: 1s per agent"
assert_file_contains "$OUT4" "❌ codex: /develop-feature smoke timed out after 1s"
assert_file_contains "$OUT4" "✅ opencode: lightweight smoke passed"
assert_file_contains "$OUT4" "Agentic doctor completed with 1 failing check(s)"

echo 'doctor e2e ok'
