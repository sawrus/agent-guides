#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
TRACE_FILE="${AGENTIC_COVERAGE_TRACE_FILE:?missing AGENTIC_COVERAGE_TRACE_FILE}"
export PS4='+${BASH_SOURCE}:${LINENO}: '
exec 9>>"$TRACE_FILE"
export BASH_XTRACEFD=9
exec bash -x "$ROOT_DIR/agentic" "$@"
