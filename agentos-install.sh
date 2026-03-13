#!/usr/bin/env bash

set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AREAS_ROOT="$REPO_ROOT/areas"
EXTENSIONS_ROOT="$REPO_ROOT/extensions"

DEFAULT_AGENT_OS="default"
STATIC_AGENT_OS=(default opencode codex claude antigravity claude cursor agents)
INSTALL_DIRS=(rules skills workflows prompts)

DRY_RUN=false
MODE="cli"
PROJECT_DIR=""
AGENT_OS="$DEFAULT_AGENT_OS"
SELECTED_AREAS=()
SELECTED_SPECS=()

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

CREATED_PATHS=()
COPIED_PATHS=()
WARNINGS=()

usage() {
  cat <<USAGE
AgentOS Installer

Usage:
  $SCRIPT_NAME list [agentos|areas|specs --area <name>]
  $SCRIPT_NAME install --project-dir <dir> [--agent-os <name>] --areas <comma_list> --specializations <comma_list>
  $SCRIPT_NAME tui

Options:
  --project-dir         Target project directory (created if missing)
  --agent-os            Target agent OS extension (default: ${DEFAULT_AGENT_OS})
  --areas               Comma-separated area list (example: software)
  --specializations     Comma-separated specializations in area.spec format (example: software.backend,software.frontend)
  --dry-run             Show actions without writing files
  -h, --help            Show this help

Examples:
  $SCRIPT_NAME list agentos
  $SCRIPT_NAME list areas
  $SCRIPT_NAME list specs --area software
  $SCRIPT_NAME install --project-dir /tmp/demo --agent-os opencode --areas software --specializations software.backend,software.frontend
  $SCRIPT_NAME tui
USAGE
}

log() {
  echo "[installer] $1"
}

warn() {
  echo "[installer][warn] $1"
  WARNINGS+=("$1")
}

unique_append() {
  local value="$1"
  local arr_name="$2"
  local item
  eval "for item in \"\${${arr_name}[@]:-}\"; do
    if [[ \"\$item\" == \"\$value\" ]]; then
      return
    fi
  done
  eval \"\${arr_name}+=(\\\"\$value\\\")\""
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

get_dest_dir() {
  local agent_os="$1"
  local bucket="$2"

  local mapping
  mapping="$(get_agent_dir_mapping "$agent_os")"
  if [[ -n "$mapping" ]]; then
    local -a parts
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

split_csv() {
  local raw="$1"
  local arr_name="$2"
  local part
  IFS=',' read -r -a parts <<< "$raw"
  for part in "${parts[@]}"; do
    part="$(trim "$part")"
    [[ -n "$part" ]] && eval "${arr_name}+=(\"\$part\")"
  done
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

copy_extension() {
  local agent_os="$1"
  local project_dir="$2"

  if [[ "$agent_os" == "$DEFAULT_AGENT_OS" ]]; then
    log "Agent OS is default: skipping extension copy"
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
      for type in "$AGENT_OS" "agents"; do
        local src="$src_root/$bucket"
        local dest_dir
        dest_dir="$(get_dest_dir "$type" "$bucket")"
        # Skip bucket if mapping is "-" (not supported by this agent OS)
        if [[ "$dest_dir" == "-" ]]; then
          log "Skip $spec_key/$bucket (not supported by '$type')"
          continue
        fi
        local dest="$project_dir/$dest_dir"
        if [[ -d "$src" ]]; then
          log "Copy $spec_key/$bucket -> $dest"
          copy_dir_contents "$src" "$dest"
        fi
      done
    done
  done
}

build_header() {
  local out="$1"
  local rules_dir
  rules_dir="$(get_dest_dir "$AGENT_OS" "rules")"
  {
    echo "# AgentOS Project Guidelines"
    echo
    echo "Generated by $SCRIPT_NAME on $(date -u +"%Y-%m-%dT%H:%M:%SZ")."
    echo
    echo "## Installation Context"
    echo "- Agent OS: $AGENT_OS"
    echo "- Agent rules directory: $rules_dir"
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
    echo "Error: --project-dir is required"
    exit 1
  fi

  if [[ "${#SELECTED_AREAS[@]}" -eq 0 ]]; then
    echo "Error: --areas is required"
    exit 1
  fi

  if [[ "${#SELECTED_SPECS[@]}" -eq 0 ]]; then
    echo "Error: --specializations is required"
    exit 1
  fi

  local area
  for area in "${SELECTED_AREAS[@]}"; do
    if ! grep -qx "$area" <<< "$available_areas"; then
      echo "Error: unknown area '$area'"
      exit 1
    fi
  done

  local spec_key
  for spec_key in "${SELECTED_SPECS[@]}"; do
    if [[ "$spec_key" != *.* ]]; then
      echo "Error: specialization must be in area.spec format: $spec_key"
      exit 1
    fi
    local area_name="${spec_key%%.*}"
    local spec_name="${spec_key#*.}"
    if [[ ! -d "$AREAS_ROOT/$area_name/$spec_name" ]]; then
      echo "Error: specialization not found: $spec_key"
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
      echo "Error: specialization '$spec_key' not included by selected areas"
      exit 1
    fi
  done

  local agentos_choices
  agentos_choices="$(get_agentos_choices)"
  if ! grep -qx "$AGENT_OS" <<< "$agentos_choices"; then
    echo "Error: unknown agent OS '$AGENT_OS'"
    exit 1
  fi
}

print_report() {
  echo
  echo "=== Installation report ==="
  echo "Project dir: $PROJECT_DIR"
  echo "Agent OS: $AGENT_OS"
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
  validate_inputs

  ensure_dir "$PROJECT_DIR"
  copy_extension "$AGENT_OS" "$PROJECT_DIR"
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
    echo "Invalid choice" >&2
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
  IFS=',' read -r -a indexes <<< "$answer"
  for idx in "${indexes[@]}"; do
    idx="$(trim "$idx")"
    if [[ ! "$idx" =~ ^[0-9]+$ ]] || (( idx < 1 || idx > ${#options[@]} )); then
      echo "Invalid selection index: $idx" >&2
      exit 1
    fi
    unique_append "${options[$((idx - 1))]}" out
  done

  printf '%s\n' "${out[@]}"
}

run_tui() {
  ascii_banner
  echo "AgentOS installer (TUI mode)"
  echo

  PROJECT_DIR="$(prompt_with_default "Target project directory" "/tmp/agentos-project")"

  agentos_choices=()
  readlines agentos_choices < <(get_agentos_choices)
  AGENT_OS="$(choose_single_by_index "Select target Agent OS:" "${agentos_choices[@]}")"

  areas=()
  readlines areas < <(list_areas)
  picked_areas=()
  readlines picked_areas < <(choose_multi_by_index "Select area(s):" "${areas[@]}")
  if [[ "${#picked_areas[@]}" -eq 0 ]]; then
    SELECTED_AREAS=(software)
  else
    SELECTED_AREAS=("${picked_areas[@]}")
  fi

  SELECTED_SPECS=()
  local area
  for area in "${SELECTED_AREAS[@]}"; do
    specs=()
    readlines specs < <(list_specs "$area")
    chosen_specs=()
    readlines chosen_specs < <(choose_multi_by_index "Select specialization(s) for area '$area':" "${specs[@]}")
    if [[ "${#chosen_specs[@]}" -eq 0 ]]; then
      echo "No specialization selected for $area" >&2
      exit 1
    fi
    local spec
    for spec in "${chosen_specs[@]}"; do
      SELECTED_SPECS+=("$area.$spec")
    done
  done

  run_install
}

if [[ $# -eq 0 ]]; then
  usage
  exit 1
fi

COMMAND="$1"
shift

case "$COMMAND" in
  list)
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
          echo "Usage: $SCRIPT_NAME list specs --area <name>"
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
          AGENT_OS="$2"
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
        --dry-run)
          DRY_RUN=true
          shift
          ;;
        -h|--help)
          usage
          exit 0
          ;;
        *)
          echo "Unknown option: $1"
          usage
          exit 1
          ;;
      esac
    done
    run_install
    ;;
  tui)
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --dry-run)
          DRY_RUN=true
          shift
          ;;
        *)
          echo "Unknown option: $1"
          usage
          exit 1
          ;;
      esac
    done
    run_tui
    ;;
  -h|--help)
    usage
    ;;
  *)
    usage
    exit 1
    ;;
esac
