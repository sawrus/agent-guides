#!/usr/bin/env sh
# Install the optional static analysis tools of repo-scan.
#   scc     - languages and line counts (used by `scan` when on PATH)
#   semgrep - detected only; call rules are planned, so it is opt-in
# Usage: install-tools.sh [scc] [semgrep]   (default: scc)
# Env: PREFIX (default ~/.local/bin), SCC_VERSION (default v4.1.0).
set -eu

PREFIX="${PREFIX:-$HOME/.local/bin}"
SCC_VERSION="${SCC_VERSION:-v4.1.0}"
TOOLS="${*:-scc}"

say() { printf '[repo-scan] %s\n' "$*" >&2; }

install_scc() {
    if command -v scc >/dev/null 2>&1; then
        say "scc already on PATH: $(command -v scc)"
        return 0
    fi
    case "$(uname -s)" in
        Linux) os=Linux ;;
        Darwin) os=Darwin ;;
        *) say "unsupported OS $(uname -s); see https://github.com/boyter/scc#install"; return 1 ;;
    esac
    case "$(uname -m)" in
        x86_64 | amd64) arch=x86_64 ;;
        arm64 | aarch64) arch=arm64 ;;
        *) say "unsupported CPU $(uname -m); see https://github.com/boyter/scc#install"; return 1 ;;
    esac
    asset="scc_${os}_${arch}.tar.gz"
    base="https://github.com/boyter/scc/releases/download/${SCC_VERSION}"
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    say "downloading scc ${SCC_VERSION} (${asset})"
    curl -fsSL -o "$tmp/$asset" "$base/$asset"
    curl -fsSL -o "$tmp/checksums.txt" "$base/checksums.txt"
    expected="$(awk -v f="$asset" '$2 == f {print $1}' "$tmp/checksums.txt")"
    if command -v sha256sum >/dev/null 2>&1; then
        actual="$(sha256sum "$tmp/$asset" | awk '{print $1}')"
    else
        actual="$(shasum -a 256 "$tmp/$asset" | awk '{print $1}')"
    fi
    if [ -z "$expected" ] || [ "$expected" != "$actual" ]; then
        say "checksum mismatch for $asset; nothing installed"
        return 1
    fi
    tar -xzf "$tmp/$asset" -C "$tmp" scc
    mkdir -p "$PREFIX"
    install -m 0755 "$tmp/scc" "$PREFIX/scc"
    say "installed $PREFIX/scc"
}

install_semgrep() {
    if command -v semgrep >/dev/null 2>&1; then
        say "semgrep already on PATH: $(command -v semgrep)"
        return 0
    fi
    if command -v pipx >/dev/null 2>&1; then
        pipx install semgrep
    elif command -v uv >/dev/null 2>&1; then
        uv tool install semgrep
    else
        say "install pipx or uv, then run: pipx install semgrep"
        return 1
    fi
}

for tool in $TOOLS; do
    case "$tool" in
        scc) install_scc ;;
        semgrep) install_semgrep ;;
        *) say "unknown tool: $tool (expected scc or semgrep)"; exit 2 ;;
    esac
done

case ":$PATH:" in
    *":$PREFIX:"*) ;;
    *) say "add $PREFIX to PATH" ;;
esac
