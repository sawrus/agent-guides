#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
"$ROOT_DIR/tests/e2e/cli.e2e.sh"
"$ROOT_DIR/tests/e2e/tui.e2e.sh"
echo 'cross e2e ok'
