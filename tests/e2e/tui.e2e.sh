#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
CLI="$ROOT_DIR/agentic"
VERSION="$(sed -n 's/^[[:space:]]*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$ROOT_DIR/package.json" | head -n 1)"
TMP_ROOT="$(mktemp -d /tmp/agentic-tui-e2e.XXXXXX)"
trap 'rm -rf "$TMP_ROOT"' EXIT
OUT="$TMP_ROOT/out.log"
set +e
"$CLI" tui >"$OUT" 2>&1
code=$?
set -e
[ "$code" -eq 1 ]
grep -Fq 'TUI mode requires an interactive terminal' "$OUT"

PYTHON_ONLY_BIN="$TMP_ROOT/python-bin"
mkdir -p "$PYTHON_ONLY_BIN"
ln -s "$(command -v python3)" "$PYTHON_ONLY_BIN/python3"
cat > "$PYTHON_ONLY_BIN/pip" <<'EOS'
#!/usr/bin/env bash
exit 0
EOS
chmod +x "$PYTHON_ONLY_BIN/pip"
OUT_VERSION="$TMP_ROOT/tui-version.log"
PROJECT="$TMP_ROOT/project"
printf '%s\n' "" "n" "$PROJECT" "2" "1" "2" "1" | \
  env HOME="$TMP_ROOT/home" AGENTIC_FORCE_INTERACTIVE=1 AGENTIC_DOCTOR=0 PATH="$PYTHON_ONLY_BIN:/usr/bin:/bin" \
  "$CLI" tui >"$OUT_VERSION" 2>&1
grep -Fq "Agentic installer (TUI mode) v$VERSION" "$OUT_VERSION"
grep -Fq "Agentic version: v$VERSION" "$OUT_VERSION"
echo 'tui e2e ok'
