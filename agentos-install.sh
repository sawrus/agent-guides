#!/usr/bin/env bash

set -euo pipefail

SCRIPT_SOURCE="${BASH_SOURCE[0]}"
SCRIPT_NAME="$(basename "$SCRIPT_SOURCE")"
REPO_ROOT="$(cd "$(dirname "$SCRIPT_SOURCE")" && pwd)"
AREAS_ROOT="$REPO_ROOT/areas"
EXTENSIONS_ROOT="$REPO_ROOT/extensions"

DEFAULT_AGENT_OS="default"
STATIC_AGENT_OS=(default opencode codex claude antigravity cursor agents)
INSTALL_DIRS=(rules skills workflows prompts)
THEME_CHOICES=(auto dark light)

DRY_RUN=false
PROJECT_DIR=""
THEME="auto"
THEME_EXPLICIT=false
ACTIVE_THEME="dark"

SELECTED_AGENT_OS=("$DEFAULT_AGENT_OS")
SELECTED_AREAS=()
SELECTED_SPECS=()

SELF_INSTALL_FORCE=false
SELF_INSTALL_BIN_DIR="${HOME}/.local/bin"
SELF_INSTALL_NAME="agentos-install"

CREATED_PATHS=()
COPIED_PATHS=()
WARNINGS=()

COLOR_RESET=""
COLOR_HEADER=""
COLOR_INFO=""
COLOR_WARN=""
COLOR_ERROR=""
COLOR_DIM=""

FZF_COLOR_ARGS=()

usage() {
  cat <<USAGE
AgentOS Installer

Usage:
  $SCRIPT_NAME list [agentos|areas|specs --area <name>]
  $SCRIPT_NAME install --project-dir <dir> [--agent-os <comma_list>] --areas <comma_list> --specializations <comma_list> [--theme auto|dark|light]
  $SCRIPT_NAME tui [--theme auto|dark|light]
  $SCRIPT_NAME self-install [--bin-dir <dir>] [--force] [--dry-run]

Behavior:
  - No arguments in interactive terminal: runs TUI mode
  - No arguments in non-interactive mode: prints usage and exits with code 1

Options:
  --project-dir         Target project directory (created if missing)
  --agent-os            Comma-separated agent OS list (default: ${DEFAULT_AGENT_OS})
  --areas               Comma-separated area list (example: software)
  --specializations     Comma-separated specializations in area.spec format (example: software.backend,software.frontend)
  --theme               Interface theme: auto|dark|light (default: auto)
  --bin-dir             Installation directory for self-install (default: ~/.local/bin)
  --force               Overwrite existing binary for self-install
  --dry-run             Show actions without writing files
  -h, --help            Show this help

Examples:
  $SCRIPT_NAME list agentos
  $SCRIPT_NAME install --project-dir /tmp/demo --agent-os opencode,codex --areas software --specializations software.backend,software.frontend
  $SCRIPT_NAME tui --theme dark
  $SCRIPT_NAME self-install --force
USAGE
}

is_interactive_terminal() {
  if [[ "${AGENTOS_FORCE_INTERACTIVE:-}" == "1" ]]; then
    return 0
  fi
  [[ -t 0 && -t 1 ]]
}

supports_color() {
  [[ -t 1 ]] || return 1
  [[ -n "${NO_COLOR:-}" ]] && return 1
  command -v tput >/dev/null 2>&1 || return 1
  local colors
  colors="$(tput colors 2>/dev/null || echo 0)"
  [[ "$colors" =~ ^[0-9]+$ ]] || return 1
  (( colors >= 8 ))
}

detect_platform() {
  if [[ -n "${AGENTOS_PLATFORM_OVERRIDE:-}" ]]; then
    echo "$AGENTOS_PLATFORM_OVERRIDE"
    return
  fi

  local uname_s
  uname_s="$(uname -s 2>/dev/null || echo unknown)"
  case "$uname_s" in
    Linux)
      echo "linux"
      ;;
    Darwin)
      echo "macos"
      ;;
    CYGWIN*|MINGW*|MSYS*)
      echo "windows"
      ;;
    *)
      echo "unknown"
      ;;
  esac
}

detect_auto_theme() {
  local bg
  bg="${COLORFGBG:-}"
  if [[ "$bg" =~ \;([0-9]{1,2})$ ]]; then
    local code="${BASH_REMATCH[1]}"
    case "$code" in
      0|1|2|3|4|5|6|8|15)
        echo "light"
        return
        ;;
      *)
        echo "dark"
        return
        ;;
    esac
  fi
  echo "dark"
}

set_theme_colors() {
  COLOR_RESET=""
  COLOR_HEADER=""
  COLOR_INFO=""
  COLOR_WARN=""
  COLOR_ERROR=""
  COLOR_DIM=""
  FZF_COLOR_ARGS=()

  if ! supports_color; then
    return
  fi

  local resolved="$THEME"
  if [[ "$resolved" == "auto" ]]; then
    resolved="$(detect_auto_theme)"
  fi
  ACTIVE_THEME="$resolved"

  case "$ACTIVE_THEME" in
    light)
      COLOR_RESET=$'\033[0m'
      COLOR_HEADER=$'\033[1;34m'
      COLOR_INFO=$'\033[1;36m'
      COLOR_WARN=$'\033[1;33m'
      COLOR_ERROR=$'\033[1;31m'
      COLOR_DIM=$'\033[2;30m'
      FZF_COLOR_ARGS=(
        "--color=fg:#1f2937,bg:#f8fafc,hl:#2563eb"
        "--color=fg+:#111827,bg+:#dbeafe,hl+:#1d4ed8"
        "--color=prompt:#0f766e,pointer:#dc2626,marker:#16a34a,spinner:#2563eb,header:#334155"
      )
      ;;
    dark|*)
      ACTIVE_THEME="dark"
      COLOR_RESET=$'\033[0m'
      COLOR_HEADER=$'\033[1;36m'
      COLOR_INFO=$'\033[1;32m'
      COLOR_WARN=$'\033[1;33m'
      COLOR_ERROR=$'\033[1;31m'
      COLOR_DIM=$'\033[2;37m'
      FZF_COLOR_ARGS=(
        "--color=fg:#e5e7eb,bg:#111827,hl:#60a5fa"
        "--color=fg+:#ffffff,bg+:#1f2937,hl+:#93c5fd"
        "--color=prompt:#22c55e,pointer:#f97316,marker:#a3e635,spinner:#06b6d4,header:#d1d5db"
      )
      ;;
  esac
}

log() {
  echo "${COLOR_INFO}[installer]${COLOR_RESET} $1"
}

warn() {
  echo "${COLOR_WARN}[installer][warn]${COLOR_RESET} $1"
  WARNINGS+=("$1")
}

error() {
  echo "${COLOR_ERROR}[installer][error]${COLOR_RESET} $1" >&2
}

unique_append() {
  local value="$1"
  local arr_name="$2"
  local item
  eval "for item in \"\${${arr_name}[@]:-}\"; do
    if [[ \"\$item\" == \"\$value\" ]]; then
      return
    fi
  done"
  eval "${arr_name}+=(\"\$value\")"
}

trim() {
  local s="$1"
  s="${s#${s%%[![:space:]]*}}"
  s="${s%${s##*[![:space:]]}}"
  echo "$s"
}

readlines() {
  local arr_name="$1"
  local line
  while IFS= read -r line || [[ -n "$line" ]]; do
    eval "${arr_name}+=(\"\$line\")"
  done
}

split_csv() {
  local raw="$1"
  local arr_name="$2"
  local part
  local parts=()
  IFS=',' read -r -a parts <<< "$raw"
  for part in "${parts[@]}"; do
    part="$(trim "$part")"
    [[ -n "$part" ]] && eval "${arr_name}+=(\"\$part\")"
  done
}

validate_theme() {
  local theme="$1"
  local item
  for item in "${THEME_CHOICES[@]}"; do
    if [[ "$item" == "$theme" ]]; then
      return 0
    fi
  done
  return 1
}

ensure_repo_layout() {
  if [[ ! -d "$AREAS_ROOT" ]]; then
    error "areas directory not found at '$AREAS_ROOT'. Run this script from an agent-guides checkout."
    exit 1
  fi
}

# Agent-specific directory mappings using case statements for Bash 3.2 compatibility
get_agent_dir_mapping() {
  local agent_os="$1"
  case "$agent_os" in
    opencode)     echo ".opencode/rules .opencode/skills .opencode/commands -" ;;
    cursor)       echo ".cursor/rules .cursor/skills - -" ;;
    kilocode)     echo ".kilocode/rules .kilocode/skills .kilocode/workflows -" ;;
    antigravity)  echo ".kilocode/rules .kilocode/skills .kilocode/workflows -" ;;
    *)            echo "" ;;
  esac
}

get_dest_dir() {
  local agent_os="$1"
  local bucket="$2"

  local mapping
  mapping="$(get_agent_dir_mapping "$agent_os")"
  if [[ -n "$mapping" ]]; then
    local parts=()
    read -r -a parts <<< "$mapping"
    local dir
    case "$bucket" in
      rules)     dir="${parts[0]}" ;;
      skills)    dir="${parts[1]}" ;;
      workflows) dir="${parts[2]}" ;;
      prompts)   dir="${parts[3]:-}" ;;
      *)         dir=".agent/$bucket" ;;
    esac
    echo "$dir"
  else
    echo ".agent/$bucket"
  fi
}

get_dynamic_agentos() {
  if [[ -d "$EXTENSIONS_ROOT" ]]; then
    find "$EXTENSIONS_ROOT" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort
  fi
}

get_agentos_choices() {
  local seen=()
  local name
  for name in "${STATIC_AGENT_OS[@]}"; do
    unique_append "$name" seen
  done
  while IFS= read -r name; do
    [[ -z "$name" ]] && continue
    unique_append "$name" seen
  done < <(get_dynamic_agentos)
  printf '%s\n' "${seen[@]}"
}

list_areas() {
  find "$AREAS_ROOT" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort | grep -v "^template$"
}

list_specs() {
  local area="$1"
  find "$AREAS_ROOT/$area" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort
}

ensure_dir() {
  local path="$1"
  if [[ "$DRY_RUN" == true ]]; then
    log "DRY-RUN mkdir -p $path"
  else
    mkdir -p "$path"
  fi
  unique_append "$path" CREATED_PATHS
}

copy_dir_contents() {
  local src="$1"
  local dest="$2"
  ensure_dir "$dest"
  if [[ "$DRY_RUN" == true ]]; then
    log "DRY-RUN cp -a $src/. $dest/"
  else
    cp -a "$src/." "$dest/"
  fi
  unique_append "$dest" COPIED_PATHS
}

normalize_selected_agent_os() {
  local normalized=()
  local agent
  if [[ "${#SELECTED_AGENT_OS[@]}" -eq 0 ]]; then
    SELECTED_AGENT_OS=("$DEFAULT_AGENT_OS")
    return
  fi
  for agent in "${SELECTED_AGENT_OS[@]}"; do
    agent="$(trim "$agent")"
    [[ -z "$agent" ]] && continue
    unique_append "$agent" normalized
  done
  if [[ "${#normalized[@]}" -eq 0 ]]; then
    normalized=("$DEFAULT_AGENT_OS")
  fi
  SELECTED_AGENT_OS=("${normalized[@]}")
}

copy_extension_for_agent() {
  local agent_os="$1"
  local project_dir="$2"

  if [[ "$agent_os" == "$DEFAULT_AGENT_OS" ]] || [[ "$agent_os" == "agents" ]]; then
    log "Agent OS '$agent_os': skipping extension copy"
    return
  fi

  local src="$EXTENSIONS_ROOT/$agent_os"
  local dest="$project_dir/.$agent_os"

  if [[ ! -d "$src" ]]; then
    warn "No extension directory found for '$agent_os' at $src (skipped)"
    return
  fi

  log "Copy extension: $src -> $dest"
  copy_dir_contents "$src" "$dest"
}

copy_extensions() {
  local project_dir="$1"
  local agent_os
  for agent_os in "${SELECTED_AGENT_OS[@]}"; do
    copy_extension_for_agent "$agent_os" "$project_dir"
  done
}

copy_specialization_assets() {
  local project_dir="$1"
  local spec_key

  for spec_key in "${SELECTED_SPECS[@]}"; do
    local area="${spec_key%%.*}"
    local spec="${spec_key#*.}"
    local src_root="$AREAS_ROOT/$area/$spec"

    if [[ ! -d "$src_root" ]]; then
      warn "Specialization path not found: $src_root"
      continue
    fi

    local bucket
    for bucket in "${INSTALL_DIRS[@]}"; do
      local src="$src_root/$bucket"
      if [[ ! -d "$src" ]]; then
        continue
      fi

      local targets=()
      local target
      for target in "${SELECTED_AGENT_OS[@]}"; do
        unique_append "$target" targets
      done
      unique_append "agents" targets

      local dest_dirs=()
      for target in "${targets[@]}"; do
        local dest_dir
        dest_dir="$(get_dest_dir "$target" "$bucket")"
        if [[ "$dest_dir" == "-" ]]; then
          log "Skip $spec_key/$bucket (not supported by '$target')"
          continue
        fi
        unique_append "$dest_dir" dest_dirs
      done

      local resolved_dir
      for resolved_dir in "${dest_dirs[@]}"; do
        local dest="$project_dir/$resolved_dir"
        log "Copy $spec_key/$bucket -> $dest"
        copy_dir_contents "$src" "$dest"
      done
    done
  done
}

build_header() {
  local out="$1"
  local rules_dir
  rules_dir="$(get_dest_dir "${SELECTED_AGENT_OS[0]}" "rules")"
  {
    echo "# AgentOS Project Guidelines"
    echo
    echo "Generated by $SCRIPT_NAME on $(date -u +"%Y-%m-%dT%H:%M:%SZ")."
    echo
    echo "## Installation Context"
    echo "- Agent OS targets: ${SELECTED_AGENT_OS[*]}"
    echo "- Primary agent rules directory: $rules_dir"
    echo "- Areas: ${SELECTED_AREAS[*]}"
    echo "- Specializations: ${SELECTED_SPECS[*]}"
    echo
    echo "---"
    echo
  } > "$out"
}

append_specialization_template() {
  local out="$1"
  local spec_key="$2"
  local area="${spec_key%%.*}"
  local spec="${spec_key#*.}"
  local src="$AREAS_ROOT/$area/$spec/AGENTS.md"

  {
    echo "## ${area}/${spec}"
    echo
    if [[ -f "$src" ]]; then
      cat "$src"
    else
      echo "No specialization AGENTS.md template found for ${spec_key}."
    fi
    echo
    echo "---"
    echo
  } >> "$out"
}

append_root_agents_template() {
  local out="$1"
  local src="$REPO_ROOT/AGENTS.md"

  {
    echo "## Shared guidance"
    echo
    if [[ -f "$src" ]]; then
      cat "$src"
    else
      echo "No root AGENTS.md template found."
    fi
    echo
    echo "---"
    echo
  } >> "$out"
}

generate_agents_md() {
  local project_dir="$1"
  local out="$project_dir/AGENTS.md"

  if [[ "$DRY_RUN" == true ]]; then
    log "DRY-RUN generate $out"
    unique_append "$out" COPIED_PATHS
    return
  fi

  ensure_dir "$project_dir"
  build_header "$out"
  append_root_agents_template "$out"

  local spec_key
  for spec_key in "${SELECTED_SPECS[@]}"; do
    append_specialization_template "$out" "$spec_key"
  done

  unique_append "$out" COPIED_PATHS
}

validate_inputs() {
  local available_areas
  available_areas="$(list_areas || true)"

  if [[ -z "$PROJECT_DIR" ]]; then
    error "--project-dir is required"
    exit 1
  fi

  if [[ "${#SELECTED_AREAS[@]}" -eq 0 ]]; then
    error "--areas is required"
    exit 1
  fi

  if [[ "${#SELECTED_SPECS[@]}" -eq 0 ]]; then
    error "--specializations is required"
    exit 1
  fi

  local area
  for area in "${SELECTED_AREAS[@]}"; do
    if ! grep -qx "$area" <<< "$available_areas"; then
      error "unknown area '$area'"
      exit 1
    fi
  done

  local spec_key
  for spec_key in "${SELECTED_SPECS[@]}"; do
    if [[ "$spec_key" != *.* ]]; then
      error "specialization must be in area.spec format: $spec_key"
      exit 1
    fi

    local area_name="${spec_key%%.*}"
    local spec_name="${spec_key#*.}"
    if [[ ! -d "$AREAS_ROOT/$area_name/$spec_name" ]]; then
      error "specialization not found: $spec_key"
      exit 1
    fi

    local found=false
    local selected_area
    for selected_area in "${SELECTED_AREAS[@]}"; do
      if [[ "$selected_area" == "$area_name" ]]; then
        found=true
        break
      fi
    done
    if [[ "$found" == false ]]; then
      error "specialization '$spec_key' not included by selected areas"
      exit 1
    fi
  done

  local agentos_choices
  agentos_choices="$(get_agentos_choices)"
  local agent
  for agent in "${SELECTED_AGENT_OS[@]}"; do
    if ! grep -qx "$agent" <<< "$agentos_choices"; then
      error "unknown agent OS '$agent'"
      exit 1
    fi
  done
}

print_report() {
  echo
  echo "${COLOR_HEADER}=== Installation report ===${COLOR_RESET}"
  echo "Project dir: $PROJECT_DIR"
  echo "Agent OS targets: ${SELECTED_AGENT_OS[*]}"
  echo "Areas: ${SELECTED_AREAS[*]}"
  echo "Specializations: ${SELECTED_SPECS[*]}"

  echo
  echo "Created directories:"
  if [[ "${#CREATED_PATHS[@]}" -eq 0 ]]; then
    echo "- (none)"
  else
    printf -- '- %s\n' "${CREATED_PATHS[@]}"
  fi

  echo
  echo "Copied/generated paths:"
  if [[ "${#COPIED_PATHS[@]}" -eq 0 ]]; then
    echo "- (none)"
  else
    printf -- '- %s\n' "${COPIED_PATHS[@]}"
  fi

  echo
  echo "Warnings:"
  if [[ "${#WARNINGS[@]}" -eq 0 ]]; then
    echo "- (none)"
  else
    printf -- '- %s\n' "${WARNINGS[@]}"
  fi
}

run_install() {
  ensure_repo_layout
  normalize_selected_agent_os
  validate_inputs

  ensure_dir "$PROJECT_DIR"
  copy_extensions "$PROJECT_DIR"
  copy_specialization_assets "$PROJECT_DIR"
  generate_agents_md "$PROJECT_DIR"
  print_report
}

ascii_banner() {
  cat <<'ART'
    _    ____ _____ _   _ _____ ___  ____
   / \  / ___| ____| \ | |_   _/ _ \/ ___|
  / _ \| |  _|  _| |  \| | | || | | \___ \
 / ___ \ |_| | |___| |\  | | || |_| |___) |
/_/   \_\____|_____|_| \_| |_| \___/|____/
ART
}

prompt_with_default() {
  local prompt="$1"
  local default="$2"
  local answer
  read -r -p "$prompt [$default]: " answer
  answer="$(trim "$answer")"
  if [[ -z "$answer" ]]; then
    echo "$default"
  else
    echo "$answer"
  fi
}

choose_single_by_index() {
  local prompt="$1"
  shift
  local options=("$@")
  local i
  echo "$prompt" >&2
  for i in "${!options[@]}"; do
    echo "  $((i + 1))) ${options[$i]}" >&2
  done
  local answer
  read -r -p "Select one (empty=1): " answer
  answer="$(trim "$answer")"
  if [[ -z "$answer" ]]; then
    echo "${options[0]}"
    return
  fi
  if [[ ! "$answer" =~ ^[0-9]+$ ]] || (( answer < 1 || answer > ${#options[@]} )); then
    error "Invalid choice"
    exit 1
  fi
  echo "${options[$((answer - 1))]}"
}

choose_multi_by_index() {
  local prompt="$1"
  shift
  local options=("$@")
  local i
  echo "$prompt" >&2
  for i in "${!options[@]}"; do
    echo "  $((i + 1))) ${options[$i]}" >&2
  done
  local answer
  read -r -p "Select one or more (comma-separated indexes): " answer
  answer="$(trim "$answer")"
  if [[ -z "$answer" ]]; then
    echo ""
    return
  fi

  local out=()
  local idx
  local indexes=()
  IFS=',' read -r -a indexes <<< "$answer"
  for idx in "${indexes[@]}"; do
    idx="$(trim "$idx")"
    if [[ ! "$idx" =~ ^[0-9]+$ ]] || (( idx < 1 || idx > ${#options[@]} )); then
      error "Invalid selection index: $idx"
      exit 1
    fi
    unique_append "${options[$((idx - 1))]}" out
  done

  printf '%s\n' "${out[@]}"
}

fzf_available() {
  command -v fzf >/dev/null 2>&1
}

run_with_sudo_if_needed() {
  if (( EUID == 0 )); then
    "$@"
    return
  fi

  if command -v sudo >/dev/null 2>&1; then
    sudo "$@"
    return
  fi

  "$@"
}

auto_install_fzf_linux() {
  if command -v apt-get >/dev/null 2>&1; then
    run_with_sudo_if_needed apt-get update
    run_with_sudo_if_needed apt-get install -y fzf
    return 0
  fi
  if command -v dnf >/dev/null 2>&1; then
    run_with_sudo_if_needed dnf install -y fzf
    return 0
  fi
  if command -v yum >/dev/null 2>&1; then
    run_with_sudo_if_needed yum install -y fzf
    return 0
  fi
  if command -v pacman >/dev/null 2>&1; then
    run_with_sudo_if_needed pacman -Sy --noconfirm fzf
    return 0
  fi
  if command -v zypper >/dev/null 2>&1; then
    run_with_sudo_if_needed zypper --non-interactive install fzf
    return 0
  fi
  if command -v apk >/dev/null 2>&1; then
    run_with_sudo_if_needed apk add --no-cache fzf
    return 0
  fi
  return 1
}

auto_install_fzf_windows() {
  if command -v winget >/dev/null 2>&1; then
    winget install --id junegunn.fzf -e --accept-source-agreements --accept-package-agreements
    return 0
  fi
  if command -v choco >/dev/null 2>&1; then
    choco install fzf -y
    return 0
  fi
  if command -v scoop >/dev/null 2>&1; then
    scoop install fzf
    return 0
  fi
  return 1
}

auto_install_fzf() {
  local platform
  platform="$(detect_platform)"

  case "$platform" in
    linux)
      auto_install_fzf_linux
      ;;
    windows)
      auto_install_fzf_windows
      ;;
    *)
      return 1
      ;;
  esac
}

ensure_fzf_or_fallback() {
  if fzf_available; then
    return 0
  fi

  warn "fzf is not installed. Falling back to index menus unless auto-install succeeds."

  if ! is_interactive_terminal; then
    return 1
  fi

  local answer
  read -r -p "Install fzf automatically now? [Y/n]: " answer
  answer="$(trim "${answer:-}")"
  if [[ -z "$answer" ]] || [[ "$answer" =~ ^[Yy]$ ]]; then
    if auto_install_fzf && fzf_available; then
      log "fzf installed successfully"
      return 0
    fi
    warn "Automatic fzf installation failed or fzf still unavailable."
    return 1
  fi

  warn "User declined automatic fzf installation."
  return 1
}

choose_single_fzf() {
  local prompt="$1"
  shift
  local options=("$@")

  if [[ "${#options[@]}" -eq 0 ]]; then
    return
  fi

  local fzf_args=(
    --ansi
    --border
    --height=70%
    --layout=reverse
    --cycle
    --no-sort
    --prompt "$prompt "
    --header "Use ↑/↓ to navigate • Enter to select"
  )
  if [[ "${#FZF_COLOR_ARGS[@]}" -gt 0 ]]; then
    fzf_args+=("${FZF_COLOR_ARGS[@]}")
  fi

  printf '%s\n' "${options[@]}" | fzf "${fzf_args[@]}"
}

choose_multi_fzf() {
  local prompt="$1"
  shift
  local options=("$@")

  if [[ "${#options[@]}" -eq 0 ]]; then
    return
  fi

  local fzf_args=(
    --ansi
    --border
    --height=75%
    --layout=reverse
    --cycle
    --no-sort
    --multi
    --bind "space:toggle"
    --bind "tab:toggle+down"
    --prompt "$prompt "
    --header "Use ↑/↓ to navigate • Space to select • Enter to confirm"
  )
  if [[ "${#FZF_COLOR_ARGS[@]}" -gt 0 ]]; then
    fzf_args+=("${FZF_COLOR_ARGS[@]}")
  fi

  printf '%s\n' "${options[@]}" | fzf "${fzf_args[@]}"
}

pick_theme_if_needed() {
  if [[ "$THEME_EXPLICIT" == true ]]; then
    return
  fi

  local selected
  if fzf_available; then
    selected="$(choose_single_fzf "Select interface theme:" "${THEME_CHOICES[@]}")"
  else
    selected="$(choose_single_by_index "Select interface theme:" "${THEME_CHOICES[@]}")"
  fi

  selected="$(trim "$selected")"
  if [[ -n "$selected" ]]; then
    THEME="$selected"
  fi
}

run_tui() {
  ensure_repo_layout

  if ! is_interactive_terminal; then
    error "TUI mode requires an interactive terminal"
    exit 1
  fi

  pick_theme_if_needed
  set_theme_colors

  ascii_banner
  echo "${COLOR_HEADER}AgentOS installer (TUI mode)${COLOR_RESET}"
  echo "${COLOR_DIM}Theme: $THEME (resolved: $ACTIVE_THEME)${COLOR_RESET}"
  echo

  local use_fzf=false
  if ensure_fzf_or_fallback; then
    use_fzf=true
    set_theme_colors
  fi

  PROJECT_DIR="$(prompt_with_default "Target project directory" "/tmp/agentos-project")"

  local agentos_choices=()
  readlines agentos_choices < <(get_agentos_choices)

  local picked_agent_os=()
  if [[ "$use_fzf" == true ]]; then
    readlines picked_agent_os < <(choose_multi_fzf "Select Agent OS target(s):" "${agentos_choices[@]}")
  else
    readlines picked_agent_os < <(choose_multi_by_index "Select Agent OS target(s):" "${agentos_choices[@]}")
  fi
  if [[ "${#picked_agent_os[@]}" -eq 0 ]]; then
    SELECTED_AGENT_OS=("$DEFAULT_AGENT_OS")
  else
    SELECTED_AGENT_OS=("${picked_agent_os[@]}")
  fi

  local areas=()
  readlines areas < <(list_areas)

  local picked_areas=()
  if [[ "$use_fzf" == true ]]; then
    readlines picked_areas < <(choose_multi_fzf "Select area(s):" "${areas[@]}")
  else
    readlines picked_areas < <(choose_multi_by_index "Select area(s):" "${areas[@]}")
  fi

  if [[ "${#picked_areas[@]}" -eq 0 ]]; then
    SELECTED_AREAS=(software)
  else
    SELECTED_AREAS=("${picked_areas[@]}")
  fi

  SELECTED_SPECS=()
  local area
  for area in "${SELECTED_AREAS[@]}"; do
    local specs=()
    readlines specs < <(list_specs "$area")

    local chosen_specs=()
    if [[ "$use_fzf" == true ]]; then
      readlines chosen_specs < <(choose_multi_fzf "Select specialization(s) for '$area':" "${specs[@]}")
    else
      readlines chosen_specs < <(choose_multi_by_index "Select specialization(s) for '$area':" "${specs[@]}")
    fi

    if [[ "${#chosen_specs[@]}" -eq 0 ]]; then
      error "No specialization selected for $area"
      exit 1
    fi

    local spec
    for spec in "${chosen_specs[@]}"; do
      SELECTED_SPECS+=("$area.$spec")
    done
  done

  run_install
}

self_install() {
  local source_path="$SCRIPT_SOURCE"
  if [[ ! -r "$source_path" ]]; then
    error "Cannot read installer source at '$source_path'."
    error "Tip: download to a local file, then run self-install from that file."
    exit 1
  fi

  local bin_dir="$SELF_INSTALL_BIN_DIR"
  if [[ "$bin_dir" == "~/.local/bin" ]]; then
    bin_dir="${HOME}/.local/bin"
  fi

  local target="$bin_dir/$SELF_INSTALL_NAME"

  ensure_dir "$bin_dir"

  if [[ -e "$target" ]] && [[ "$SELF_INSTALL_FORCE" != true ]]; then
    error "Target already exists: $target"
    error "Use --force to overwrite"
    exit 1
  fi

  if [[ "$DRY_RUN" == true ]]; then
    log "DRY-RUN install script to $target"
  else
    cp "$source_path" "$target"
    chmod +x "$target"
    unique_append "$target" COPIED_PATHS
    log "Installed: $target"
  fi

  case ":$PATH:" in
    *":$bin_dir:"*)
      log "PATH already includes $bin_dir"
      ;;
    *)
      warn "PATH does not include $bin_dir"
      warn "Add this to your shell profile: export PATH=\"$bin_dir:\$PATH\""
      ;;
  esac

  echo
  echo "${COLOR_HEADER}=== Self-install report ===${COLOR_RESET}"
  echo "Source: $source_path"
  echo "Target: $target"
  echo "Dry-run: $DRY_RUN"
}

parse_theme_option() {
  local value="$1"
  if ! validate_theme "$value"; then
    error "Invalid --theme value '$value'. Allowed: auto|dark|light"
    exit 1
  fi
  THEME="$value"
  THEME_EXPLICIT=true
}

handle_no_args() {
  if is_interactive_terminal; then
    run_tui
    exit 0
  fi

  usage
  exit 1
}

set_theme_colors

if [[ $# -eq 0 ]]; then
  handle_no_args
fi

COMMAND="$1"
shift

case "$COMMAND" in
  list)
    ensure_repo_layout
    SUBCOMMAND="${1:-}"
    case "$SUBCOMMAND" in
      agentos)
        get_agentos_choices
        ;;
      areas)
        list_areas
        ;;
      specs)
        shift || true
        if [[ "${1:-}" != "--area" ]] || [[ -z "${2:-}" ]]; then
          error "Usage: $SCRIPT_NAME list specs --area <name>"
          exit 1
        fi
        list_specs "$2"
        ;;
      *)
        usage
        exit 1
        ;;
    esac
    ;;

  install)
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --project-dir)
          PROJECT_DIR="$2"
          shift 2
          ;;
        --agent-os)
          split_csv "$2" SELECTED_AGENT_OS
          shift 2
          ;;
        --areas)
          split_csv "$2" SELECTED_AREAS
          shift 2
          ;;
        --specializations)
          split_csv "$2" SELECTED_SPECS
          shift 2
          ;;
        --theme)
          parse_theme_option "$2"
          shift 2
          ;;
        --dry-run)
          DRY_RUN=true
          shift
          ;;
        -h|--help)
          usage
          exit 0
          ;;
        *)
          error "Unknown option: $1"
          usage
          exit 1
          ;;
      esac
    done
    set_theme_colors
    run_install
    ;;

  tui)
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --theme)
          parse_theme_option "$2"
          shift 2
          ;;
        --dry-run)
          DRY_RUN=true
          shift
          ;;
        -h|--help)
          usage
          exit 0
          ;;
        *)
          error "Unknown option: $1"
          usage
          exit 1
          ;;
      esac
    done
    run_tui
    ;;

  self-install)
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --bin-dir)
          SELF_INSTALL_BIN_DIR="$2"
          shift 2
          ;;
        --force)
          SELF_INSTALL_FORCE=true
          shift
          ;;
        --theme)
          parse_theme_option "$2"
          shift 2
          ;;
        --dry-run)
          DRY_RUN=true
          shift
          ;;
        -h|--help)
          usage
          exit 0
          ;;
        *)
          error "Unknown option: $1"
          usage
          exit 1
          ;;
      esac
    done
    set_theme_colors
    self_install
    ;;

  -h|--help)
    usage
    ;;

  *)
    usage
    exit 1
    ;;
esac
