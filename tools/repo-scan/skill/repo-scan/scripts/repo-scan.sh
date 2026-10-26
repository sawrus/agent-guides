#!/usr/bin/env bash
# repo-scan.sh — run tools/repo-scan of agent-guides from the repo-scan skill.
#
# Usage:
#   repo-scan.sh run   [REPO|ROOT ...] [options]   # stage 1 + stage 2 (LLM)
#   repo-scan.sh scan  [REPO|ROOT ...] [options]   # stage 1 only (no LLM, no network)
#   repo-scan.sh llm   [options]                   # stage 2 over the last scan (--in defaults to the out dir)
#   repo-scan.sh gate-propose|gate-verify [args]   # .agent/gate.json candidates / verification
#   repo-scan.sh check [--llm-claude]              # requirements (python3 >= 3.11, git; offers scc)
#   repo-scan.sh tools [scc] [semgrep]             # install optional tools
#   repo-scan.sh home                              # print the agent-guides directory
#
# A REPO argument (a directory with .git) is the focus: the context roots are scanned so its links
# resolve, and only its view is written. Without positional arguments REPO_SCAN_ROOTS is scanned.
#
# Settings (first found wins per variable): environment, ~/.config/agentic/repo-scan.env, <skill>/defaults.env.
#   REPO_SCAN_ROOTS          group directories for a scan of many repositories
#   REPO_SCAN_ROOT_URLS      "DIR=URL ..." GitLab URL per root (optional; inferred from the path otherwise)
#   REPO_SCAN_CONTEXT_ROOTS  roots scanned to resolve links of one repository (default: REPO_SCAN_ROOTS)
#   REPO_SCAN_OUT            output directory (default: ~/.cache/agentic/repo-scan/<repo name or "all">)
#   REPO_SCAN_PROVIDER, REPO_SCAN_MODEL   stage 2 provider (claude | litellm) and model
#   AGENTIC_LLM_BASE_URL, AGENTIC_LLM_MODEL   LiteLLM endpoint and model; the key only from AGENTIC_LLM_API_KEY
# agent-guides directory: $AGENT_GUIDES_HOME, the checkout that contains this skill, the path in
# ~/.config/agentic/agent-guides-home, else ~/.local/share/agent-guides (cloned on first use).
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_URL="https://github.com/sawrus/agent-guides.git"
DEFAULT_HOME="${HOME}/.local/share/agent-guides"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}/agentic"

if [[ $# -eq 0 || "$1" == "-h" || "$1" == "--help" ]]; then
  grep '^#' "$0" | sed 's/^# \{0,1\}//' | tail -n +2
  exit 0
fi

# Settings files never override the environment; keys are not read from them.
load_settings() {
  local file line key value
  for file in "$CONFIG_HOME/repo-scan.env" "$SKILL_DIR/defaults.env"; do
    [[ -f "$file" ]] || continue
    while IFS= read -r line || [[ -n "$line" ]]; do
      [[ "$line" =~ ^[[:space:]]*([A-Z_][A-Z0-9_]*)=(.*)$ ]] || continue
      key="${BASH_REMATCH[1]}"
      value="${BASH_REMATCH[2]}"
      value="${value%\"}"; value="${value#\"}"
      [[ "$key" == *KEY* || "$key" == *TOKEN* ]] && continue
      [[ -n "${!key:-}" ]] && continue
      export "$key=${value//\~/$HOME}"
    done <"$file"
  done
}

resolve_home() {
  local up
  if [[ -n "${AGENT_GUIDES_HOME:-}" ]]; then
    echo "${AGENT_GUIDES_HOME/#\~/$HOME}"; return
  fi
  up="$(cd "$SKILL_DIR/../../../.." 2>/dev/null && pwd || true)"
  if [[ -n "$up" && -f "$up/tools/repo-scan/repo_scan.py" ]]; then
    echo "$up"; return
  fi
  if [[ -s "$CONFIG_HOME/agent-guides-home" ]]; then
    local saved
    saved="$(head -1 "$CONFIG_HOME/agent-guides-home")"
    echo "${saved/#\~/$HOME}"; return
  fi
  echo "$DEFAULT_HOME"
}

load_settings
home="$(resolve_home)"
if [[ ! -d "$home/.git" && ! -f "$home/tools/repo-scan/repo_scan.py" ]]; then
  echo "repo-scan: agent-guides not found in $home, cloning $REPO_URL ..." >&2
  mkdir -p "$(dirname "$home")"
  git clone -q "$REPO_URL" "$home"
fi
tool="$home/tools/repo-scan"
if [[ ! -f "$tool/repo_scan.py" ]]; then
  echo "repo-scan: $tool is missing; agent-guides >= 2.1.0 is needed (git -C $home pull)" >&2
  exit 1
fi

cmd="$1"; shift
case "$cmd" in
  home) echo "$home"; exit 0 ;;
  check) exec sh "$tool/check-tools.sh" "$@" ;;
  tools) exec sh "$tool/install-tools.sh" "$@" ;;
esac

# Positional targets come first; options follow.
targets=()
while [[ $# -gt 0 && "$1" != -* ]]; do targets+=("${1/#\~/$HOME}"); shift; done
has_opt() { local o; for o in "${@:2}"; do [[ "$o" == "$1" || "$o" == "$1="* ]] && return 0; done; return 1; }

default_out() {
  if [[ -n "${REPO_SCAN_OUT:-}" ]]; then echo "${REPO_SCAN_OUT/#\~/$HOME}"; return; fi
  if [[ ${#targets[@]} -eq 1 && -e "${targets[0]}/.git" ]]; then
    echo "$HOME/.cache/agentic/repo-scan/$(basename "${targets[0]}")"
  else
    echo "$HOME/.cache/agentic/repo-scan/all"
  fi
}

py=(env PYTHONDONTWRITEBYTECODE=1 python3 "$tool/repo_scan.py")
case "$cmd" in
  run | scan)
    sh "$tool/check-tools.sh" $([[ "$cmd" == run && "${REPO_SCAN_PROVIDER:-claude}" == claude ]] && echo --llm-claude)
    if [[ ${#targets[@]} -eq 0 ]]; then
      [[ -n "${REPO_SCAN_ROOTS:-}" ]] || { echo "repo-scan: give REPO|ROOT arguments or set REPO_SCAN_ROOTS" >&2; exit 2; }
      read -r -a targets <<<"${REPO_SCAN_ROOTS//\~/$HOME}"
    fi
    export REPO_SCAN_CONTEXT_ROOTS="${REPO_SCAN_CONTEXT_ROOTS:-${REPO_SCAN_ROOTS:-}}"
    REPO_SCAN_CONTEXT_ROOTS="${REPO_SCAN_CONTEXT_ROOTS//\~/$HOME}"
    [[ -n "$REPO_SCAN_CONTEXT_ROOTS" ]] || unset REPO_SCAN_CONTEXT_ROOTS
    extra=()
    has_opt --out "$@" || extra+=(--out "$(default_out)")
    for pair in ${REPO_SCAN_ROOT_URLS:-}; do extra+=(--root-url "${pair//\~/$HOME}"); done
    if [[ "$cmd" == run ]]; then
      has_opt --provider "$@" || extra+=(--provider "${REPO_SCAN_PROVIDER:-claude}")
      if ! has_opt --model "$@" && [[ -n "${REPO_SCAN_MODEL:-}" ]]; then extra+=(--model "$REPO_SCAN_MODEL"); fi
    fi
    exec "${py[@]}" "$cmd" "${targets[@]}" "${extra[@]}" "$@"
    ;;
  llm | gate-propose | gate-verify)
    extra=()
    has_opt --in "$@" || extra+=(--in "$(default_out)")
    if [[ "$cmd" == llm ]]; then
      has_opt --provider "$@" || extra+=(--provider "${REPO_SCAN_PROVIDER:-claude}")
      if ! has_opt --model "$@" && [[ -n "${REPO_SCAN_MODEL:-}" ]]; then extra+=(--model "$REPO_SCAN_MODEL"); fi
      for t in "${targets[@]}"; do extra+=(--repo "$t"); done  # llm takes repositories as --repo
      targets=()
    fi
    exec "${py[@]}" "$cmd" "${targets[@]}" "${extra[@]}" "$@"
    ;;
  *) echo "repo-scan: unknown command '$cmd' (see --help)" >&2; exit 2 ;;
esac
