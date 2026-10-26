#!/usr/bin/env sh
# Check what repo-scan needs before it runs. Plain sh, so it works where Python is missing.
#   required: python3 >= 3.11, git
#   optional: scc (line counts), semgrep (detected only), claude (llm --provider claude), curl + tar (installer)
# Usage: check-tools.sh [--llm-claude]
# On a terminal it offers to install a missing scc; REPO_SCAN_NO_PROMPT=1 turns the offer off.
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
missing=0
say() { printf '[repo-scan] %s\n' "$*" >&2; }

os_hint() {
    # $1 = apt package, $2 = brew formula
    if command -v apt-get >/dev/null 2>&1; then
        echo "sudo apt-get install -y $1"
    elif command -v dnf >/dev/null 2>&1; then
        echo "sudo dnf install -y $1"
    elif command -v brew >/dev/null 2>&1; then
        echo "brew install $2"
    else
        echo "install $1 with your package manager"
    fi
}

# Required: python3 >= 3.11 (tomllib).
if ! command -v python3 >/dev/null 2>&1; then
    say "missing: python3 >= 3.11 (required)"
    say "  install: $(os_hint python3 python@3.12)   or: uv python install 3.12"
    missing=1
elif ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    say "python3 is $(python3 -c 'import platform; print(platform.python_version())'); repo-scan needs >= 3.11 (required)"
    say "  install: $(os_hint python3.12 python@3.12)   or: uv python install 3.12"
    missing=1
fi

# Required: git (repository discovery and history).
if ! command -v git >/dev/null 2>&1; then
    say "missing: git (required)"
    say "  install: $(os_hint git git)"
    missing=1
fi

# Optional: claude CLI, only for `llm --provider claude`.
if [ "${1:-}" = "--llm-claude" ] && ! command -v claude >/dev/null 2>&1; then
    say "missing: claude CLI (needed for llm --provider claude); use --provider litellm or install Claude Code"
    missing=1
fi

[ "$missing" -eq 0 ] || exit 1

# Optional: scc. Without it the built-in counter runs.
if ! command -v scc >/dev/null 2>&1; then
    say "optional scc is not installed; the built-in line counter will run"
    if [ -t 0 ] && [ -t 2 ] && [ -z "${REPO_SCAN_NO_PROMPT:-}" ]; then
        if ! command -v curl >/dev/null 2>&1 || ! command -v tar >/dev/null 2>&1; then
            say "  the installer needs curl and tar: $(os_hint 'curl tar' curl)"
        else
            printf '[repo-scan] install scc into %s now? [y/N] ' "${PREFIX:-$HOME/.local/bin}" >&2
            read -r answer || answer=""
            case "$answer" in
                y | Y | yes | YES) sh "$HERE/install-tools.sh" scc || say "scc install failed; continuing without it" ;;
                *) say "  later: make repo-scan-tools" ;;
            esac
        fi
    else
        say "  install: make repo-scan-tools"
    fi
fi
if ! command -v semgrep >/dev/null 2>&1; then
    say "optional semgrep is not installed (not used yet; make repo-scan-tools REPO_SCAN_TOOLS='scc semgrep')"
fi
exit 0
