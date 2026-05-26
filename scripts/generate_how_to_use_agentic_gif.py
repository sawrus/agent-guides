#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROMPT = "Define acceptance criteria for a tiny CLI that greets a user by name. Keep it short."
ROLE_ORDER = ["product-owner", "pm", "team-lead", "developer", "qa", "designer", "devops-engineer"]
GIF_WIDTH = 820
GIF_HEIGHT = 522
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate images/how_to_use_agentic.gif from a reproducible agentic TUI/fzf "
            "walkthrough plus a real OpenCode product-owner run."
        )
    )
    parser.add_argument("--output", default=str(ROOT / "images/how_to_use_agentic.gif"), help="GIF output path")
    parser.add_argument("--tmp-root", help="Keep/use this temporary working directory")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Prompt sent to OpenCode product-owner")
    parser.add_argument("--fps", type=int, default=4, help="GIF frame rate")
    parser.add_argument("--target-seconds", type=float, default=55.0, help="Approximate final GIF duration")
    parser.add_argument("--agentic", default=str(ROOT / "agentic"), help="agentic executable to run")
    parser.add_argument("--opencode", default="opencode", help="opencode executable to run")
    parser.add_argument(
        "--project-name",
        default="agentic-opencode-demo",
        help="Display name used in the GIF for the temporary target project",
    )
    parser.add_argument(
        "--skip-opencode",
        action="store_true",
        help="Render the TUI install GIF without running OpenCode; useful for testing rendering only",
    )
    return parser.parse_args()


def require_tool(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise SystemExit(f"Missing required tool on PATH: {name}")
    return found


def run(command: list[str], *, env: dict[str, str] | None = None, cwd: Path = ROOT, output: Path | None = None) -> None:
    if output:
        with output.open("w", encoding="utf-8") as handle:
            subprocess.run(command, cwd=cwd, env=env, stdout=handle, stderr=subprocess.STDOUT, check=True)
    else:
        subprocess.run(command, cwd=cwd, env=env, check=True)


def copy_opencode_state(real_home: Path, demo_home: Path) -> None:
    (demo_home / ".config").mkdir(parents=True, exist_ok=True)
    (demo_home / ".local/share/opencode").mkdir(parents=True, exist_ok=True)
    (demo_home / ".cache").mkdir(parents=True, exist_ok=True)

    config_dir = real_home / ".config/opencode"
    if config_dir.exists():
        shutil.copytree(config_dir, demo_home / ".config/opencode", dirs_exist_ok=True)

    auth_file = real_home / ".local/share/opencode/auth.json"
    if auth_file.exists():
        shutil.copy2(auth_file, demo_home / ".local/share/opencode/auth.json")

    cache_dir = real_home / ".cache/opencode"
    if cache_dir.exists():
        shutil.copytree(cache_dir, demo_home / ".cache/opencode", dirs_exist_ok=True)


def write_fzf_driver(path: Path) -> None:
    path.write_text(
        r'''#!/usr/bin/env bash
set -euo pipefail

prompt=""
header=""
print_query=false
while [ "$#" -gt 0 ]; do
  case "$1" in
    --prompt) shift; prompt="${1:-}" ;;
    --header) shift; header="${1:-}" ;;
    --print-query) print_query=true ;;
  esac
  shift || true
done

input="$(cat)"
log="${AGENTIC_FAKE_FZF_LOG:-/tmp/agentic-fake-fzf.log}"
{
  printf '%s\n' "--- prompt: $prompt"
  printf '%s\n' "--- header: $header"
  printf '%s\n' "$input"
} >> "$log"

choose_copilot() {
  count_file="${AGENTIC_FAKE_FZF_COUNT:-/tmp/agentic-fake-fzf-count}"
  n=0
  [ -f "$count_file" ] && n="$(cat "$count_file" 2>/dev/null || printf 0)"
  n=$((n + 1))
  printf '%s\n' "$n" > "$count_file"
  copilot="$(printf '%s\n' "$input" | awk -v n="$n" 'BEGIN{c=0} /github-copilot\// {c++; lines[c]=$0} END{if(c>0){idx=((n-1)%c)+1; print lines[idx]}}')"
  if [ -n "$copilot" ]; then
    printf '%s\n' "$copilot"
  else
    printf '%s\n' "$(printf '%s\n' "$input" | sed -n '1p')"
  fi
}

case "$prompt" in
  "Select interface theme:"*) printf 'dark\n' ;;
  "Target project directory"*)
    if [ "$print_query" = true ]; then
      printf '%s\n<press Enter to confirm path>\n' "${AGENTIC_DEMO_PROJECT:-/tmp/agentic-opencode-demo}"
    else
      printf '%s\n' "${AGENTIC_DEMO_PROJECT:-/tmp/agentic-opencode-demo}"
    fi
    ;;
  "Select Agent OS target"*) printf 'opencode\n' ;;
  "Select optional MCP integration"*) printf 'context7\nmempalace\n' ;;
  "Context7 API key mode:"*) printf 'Use without API key\n' ;;
  "Select area"*) printf 'software\n' ;;
  "Select specialization"*) printf 'backend\ngeneral\n' ;;
  "Select optional OpenCode plugin"*) printf 'telegram-notification\nagent-model-mapper\n' ;;
  "Telegram botToken"*)
    if [ "$print_query" = true ]; then printf 'demo-token\n<press Enter to confirm>\n'; else printf 'demo-token\n'; fi
    ;;
  "Telegram chatId"*)
    if [ "$print_query" = true ]; then printf 'demo-chat\n<press Enter to confirm>\n'; else printf 'demo-chat\n'; fi
    ;;
  "Save OpenCode model mapping?"*) printf 'Confirm\n' ;;
  *" main> "*|*" fallback> "*) choose_copilot ;;
  *) printf '%s\n' "$(printf '%s\n' "$input" | sed -n '1p')" ;;
esac
''',
        encoding="utf-8",
    )
    path.chmod(0o755)


def run_agentic_tui(args: argparse.Namespace, tmp_root: Path, project_dir: Path, demo_home: Path) -> Path:
    fake_bin = tmp_root / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    write_fzf_driver(fake_bin / "fzf")

    env = os.environ.copy()
    env.update(
        {
            "HOME": str(demo_home),
            "XDG_CONFIG_HOME": str(tmp_root / "xdg-config"),
            "XDG_DATA_HOME": str(tmp_root / "xdg-data"),
            "PATH": f"{fake_bin}:{env.get('PATH', '')}",
            "AGENTIC_FORCE_INTERACTIVE": "1",
            "AGENTIC_DEMO_PROJECT": str(project_dir),
            "AGENTIC_FAKE_FZF_LOG": str(tmp_root / "fzf.log"),
            "AGENTIC_FAKE_FZF_COUNT": str(tmp_root / "fzf-count"),
            "AGENTIC_MEMPALACE_SETUP": "skip",
            "AGENTIC_DOCTOR": "0",
        }
    )
    output = tmp_root / "agentic-tui.out"
    run([args.agentic, "tui"], env=env, output=output)
    return output


def run_opencode(args: argparse.Namespace, tmp_root: Path, project_dir: Path, demo_home: Path) -> Path:
    output = tmp_root / "opencode-product-owner.out"
    if args.skip_opencode:
        output.write_text(
            "> product-owner · github-copilot/gpt-5.4\n"
            "Acceptance criteria\n"
            "1. The CLI accepts a user name as input via a required argument, e.g. `greet Alice`.\n"
            "2. When a valid name is provided, the CLI prints exactly: `Hello, Alice!`\n"
            "3. If no name is provided, the CLI shows a clear usage/error message and exits non-zero.\n"
            "4. The CLI exits with status code `0` on successful greeting output.\n"
            "5. The greeting is written to standard output only.\n",
            encoding="utf-8",
        )
        return output

    env = os.environ.copy()
    env.update({"HOME": str(demo_home), "OPENCODE_DISABLE_AUTOUPDATE": "1"})
    run(
        [
            args.opencode,
            "run",
            "--dir",
            str(project_dir),
            "--agent",
            "product-owner",
            "--dangerously-skip-permissions",
            args.prompt,
        ],
        env=env,
        output=output,
    )
    return output


def read_mappings(project_dir: Path) -> list[tuple[str, str, str]]:
    config = json.loads((project_dir / ".opencode/opencode.json").read_text(encoding="utf-8"))
    mappings: list[tuple[str, str, str]] = []
    for role in ROLE_ORDER:
        agent = config["agent"][role]
        model = agent.get("model", "")
        fallback = (agent.get("fallback") or [""])[0]
        if not model.startswith("github-copilot/"):
            raise SystemExit(f"Generated non-Copilot model for {role}: {model}")
        if fallback and not fallback.startswith("github-copilot/"):
            raise SystemExit(f"Generated non-Copilot fallback for {role}: {fallback}")
        mappings.append((role, model, fallback))
    return mappings


def clean_opencode_output(path: Path) -> list[str]:
    raw = ANSI_RE.sub("", path.read_text(encoding="utf-8", errors="replace"))
    lines: list[str] = []
    for line in raw.splitlines():
        line = line.strip("\r")
        if not line.strip():
            continue
        lowered = line.lower()
        if "sqlite-migration" in lowered or "database migration" in lowered:
            continue
        line = line.replace("—", "-").replace("Here’s", "Here's").replace("· gpt-5.4", "· github-copilot/gpt-5.4")
        lines.append(line)
    return lines


def build_slides(
    args: argparse.Namespace,
    mappings: list[tuple[str, str, str]],
    opencode_lines: list[str],
) -> list[dict]:
    slides: list[dict] = []

    def terminal(duration: float, lines: list[tuple[str, str]]) -> None:
        slides.append({"kind": "terminal", "duration": duration, "lines": lines})

    def fzf(
        duration: float,
        prompt: str,
        header: str,
        options: list[str],
        selected: list[str] | None = None,
        cursor: int = 0,
        query: str | None = None,
    ) -> None:
        slides.append(
            {
                "kind": "fzf",
                "duration": duration,
                "prompt": prompt,
                "header": header,
                "options": options,
                "selected": set(selected or []),
                "cursor": cursor,
                "query": query,
            }
        )

    terminal(
        2.4,
        [
            ("cmd", "$ ./agentic tui"),
            ("normal", ""),
            ("title", "    _    ____ _____ _   _ _____ ___ ____"),
            ("title", "   / \\  / ___| ____| \\ | |_   _|_ _/ ___|"),
            ("title", "  / _ \\| |  _|  _| |  \\| | | |  | | |"),
            ("title", " / ___ \\ |_| | |___| |\\  | | |  | | |___"),
            ("title", "/_/   \\_\\____|_____|_| \\_| |_| |___\\____|"),
            ("section", "Agentic installer (TUI mode) v0.3.1"),
            ("dim", "Theme: dark (resolved: dark)"),
        ],
    )
    fzf(2.2, "Target project directory [/tmp/agentic-project]:", "Type path and press Enter to confirm", ["<press Enter to confirm path>"], query=f"/tmp/{args.project_name}")
    fzf(3.0, "Select Agent OS target(s):", "Use Up/Down to navigate - Space to select - Enter to confirm", ["default", "opencode", "codex", "claude", "antigravity", "cursor", "kilocode", "gemini"], ["opencode"], 1)
    fzf(3.0, "Select optional MCP integration(s):", "Use Up/Down to navigate - Space to select - Enter to confirm", ["<none>", "context7", "mempalace"], ["context7", "mempalace"], 2)
    fzf(2.4, "Context7 API key mode:", "Use Up/Down to navigate - Enter to select", ["Use without API key", "Enter CONTEXT7_API_KEY"], ["Use without API key"], 0)
    fzf(2.6, "Select area(s):", "Use Up/Down to navigate - Space to select - Enter to confirm", ["devops", "software"], ["software"], 1)
    fzf(3.4, "Select specialization(s) for 'software':", "Use Up/Down to navigate - Space to select - Enter to confirm", ["backend", "data-engineering", "frontend", "full-stack", "general", "mlops", "mobile", "platform", "qa", "security"], ["backend", "general"], 4)
    fzf(3.2, "Select optional OpenCode plugin(s):", "Use Up/Down to navigate - Space to select - Enter to confirm", ["<none>", "telegram-notification", "agent-model-mapper"], ["telegram-notification", "agent-model-mapper"], 2)
    terminal(
        2.0,
        [
            ("section", "OpenCode plugins selected"),
            ("ok", "telegram-notification enabled"),
            ("ok", "agent-model-mapper enabled"),
            ("dim", "Telegram credentials entered for this temporary demo project"),
        ],
    )

    model_options = [
        "github-copilot/gpt-4o",
        "github-copilot/claude-sonnet-4.6",
        "github-copilot/gpt-5.2",
        "github-copilot/claude-sonnet-4.5",
        "github-copilot/gemini-2.5-pro",
        "github-copilot/grok-code-fast-1",
        "github-copilot/claude-opus-4.6",
        "github-copilot/gpt-4.1",
        "github-copilot/gpt-5.4",
        "github-copilot/gpt-5.4-mini",
        "github-copilot/claude-haiku-4.5",
        "github-copilot/gemini-3.1-pro-preview",
        "github-copilot/gpt-5.5",
    ]
    for role, model, _fallback in mappings[:3]:
        cursor = model_options.index(model) if model in model_options else 0
        fzf(2.0, f"{role} main>", f"Select main model for {role}", model_options[:10], [model], min(cursor, 9))

    terminal(
        4.2,
        [("section", "agent-model-mapper: GitHub Copilot models")]
        + [("ok", f"{role}: main={model} fallback={fallback}") for role, model, fallback in mappings],
    )
    fzf(2.0, "Save OpenCode model mapping?", "All Agentic roles mapped to github-copilot/* models", ["Confirm", "Cancel"], ["Confirm"], 0)
    terminal(
        5.8,
        [
            ("cmd", "2026-05-22 17:02:51 [agentic] Run log initialized"),
            ("ok", "telegram-notification enabled"),
            ("section", "agent-model-mapper: choose OpenCode models for Agentic roles"),
            ("ok", "agent-model-mapper: updated .opencode/opencode.json"),
            ("ok", "Context7 MCP configured without an API key."),
            ("ok", "MemPalace MCP binary found: mempalace-mcp"),
            ("section", "=== Installation report ==="),
            ("ok", "Agent OS targets: opencode"),
            ("ok", "Specializations: software.backend software.general"),
            ("ok", "Created directories: 24"),
            ("ok", "Copied/generated paths: 89"),
            ("ok", "Warnings: (none)"),
        ],
    )
    terminal(
        2.6,
        [
            ("cmd", f"$ cd /tmp/{args.project_name}"),
            ("cmd", "$ opencode run --agent product-owner \\"),
            ("cmd", f'    "{args.prompt}"'),
        ],
    )

    output_rows: list[tuple[str, str]] = []
    for line in opencode_lines:
        style = "normal"
        if line.startswith("agent-model-mapper"):
            style = "ok"
        elif line.startswith("> product-owner"):
            style = "agent"
        elif line.startswith("**"):
            style = "section"
            line = line.strip("*")
        elif re.match(r"^[0-9]+\.", line):
            style = "ok"
        for part in textwrap.wrap(line, width=92, replace_whitespace=False, drop_whitespace=False) or [""]:
            output_rows.append((style, part))
    terminal(6.8, output_rows[:18])
    terminal(3.0, [("ok", "Done: Agentic TUI installed OpenCode guidance; Product Owner answered through github-copilot/gpt-5.4.")])

    total = sum(slide["duration"] for slide in slides)
    if args.target_seconds > 0:
        scale = args.target_seconds / total
        for slide in slides:
            slide["duration"] *= scale
    return slides


def render_gif(slides: list[dict], output: Path, tmp_root: Path, fps: int) -> None:
    require_tool("rsvg-convert")
    require_tool("ffmpeg")

    frames_dir = tmp_root / "tui_frames"
    svg_dir = tmp_root / "tui_svg"
    for directory in (frames_dir, svg_dir):
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True)

    colors = {
        "bg": "#101418",
        "bar": "#1c232b",
        "border": "#2c3640",
        "normal": "#d6deeb",
        "dim": "#8b98a7",
        "cmd": "#8bd5ff",
        "ok": "#a6e3a1",
        "warn": "#f9e2af",
        "section": "#f5c2e7",
        "title": "#ffffff",
        "agent": "#94e2d5",
        "selected": "#0f2f3a",
        "accent": "#89dceb",
    }

    def text_node(x: int, y: int, text: str, style: str = "normal", *, weight: str | None = None, size: int | None = None) -> str:
        color = colors.get(style, colors["normal"])
        weight = weight or ("700" if style in {"title", "section", "agent"} else "400")
        size = size or (14 if style == "title" else 13)
        return (
            f'<text x="{x}" y="{y}" fill="{color}" font-family="Menlo, Monaco, monospace" '
            f'font-size="{size}" font-weight="{weight}" xml:space="preserve">{html.escape(text)}</text>'
        )

    def base(nodes: list[str]) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{GIF_WIDTH}" height="{GIF_HEIGHT}" '
            f'viewBox="0 0 {GIF_WIDTH} {GIF_HEIGHT}">'
            f'<rect width="{GIF_WIDTH}" height="{GIF_HEIGHT}" fill="{colors["bg"]}"/>'
            f'<rect x="0" y="0" width="{GIF_WIDTH}" height="34" fill="{colors["bar"]}"/>'
            '<circle cx="20" cy="17" r="5" fill="#ff5f57"/>'
            '<circle cx="38" cy="17" r="5" fill="#ffbd2e"/>'
            '<circle cx="56" cy="17" r="5" fill="#28c840"/>'
            f'{text_node(76, 22, "agentic tui - OpenCode setup", "dim", size=12)}'
            f'<rect x="0.5" y="0.5" width="{GIF_WIDTH - 1}" height="{GIF_HEIGHT - 1}" fill="none" stroke="{colors["border"]}"/>'
            f'{"".join(nodes)}</svg>'
        )

    def render_terminal(slide: dict) -> str:
        nodes: list[str] = []
        y = 58
        for style, line in slide["lines"][-25:]:
            nodes.append(text_node(18, y, line, style))
            y += 17
        return base(nodes)

    def render_fzf(slide: dict) -> str:
        nodes = [text_node(18, 54, "$ ./agentic tui", "cmd")]
        px, py, pw, ph = 28, 92, 764, 390
        nodes.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="4" fill="#0b1117" stroke="{colors["border"]}"/>')
        nodes.append(text_node(px + 16, py + 28, slide["header"], "dim", size=12))
        if slide.get("query") is not None:
            nodes.append(text_node(px + 16, py + 58, f'{slide["prompt"]} {slide["query"]}', "cmd"))
            opt_y = py + 92
        else:
            nodes.append(text_node(px + 16, py + 58, slide["prompt"], "cmd"))
            opt_y = py + 90

        selected = slide["selected"]
        cursor = slide["cursor"]
        options = slide["options"]
        start = 0
        max_opts = 16
        if len(options) > max_opts:
            start = max(0, min(cursor - 7, len(options) - max_opts))
        visible = options[start : start + max_opts]
        for index, option in enumerate(visible, start):
            yy = opt_y + (index - start) * 22
            is_cursor = index == cursor
            is_selected = option in selected
            if is_cursor:
                nodes.append(f'<rect x="{px + 10}" y="{yy - 15}" width="{pw - 20}" height="21" fill="{colors["selected"]}"/>')
            marker = "[x]" if is_selected else "[ ]"
            prefix = "> " if is_cursor else "  "
            style = "ok" if is_selected else ("accent" if is_cursor else "normal")
            nodes.append(text_node(px + 18, yy, f"{prefix}{marker} {option}", style))
        nodes.append(text_node(px + 16, py + ph - 18, "Space: toggle   Enter: confirm   fzf", "dim", size=12))
        return base(nodes)

    cumulative: list[tuple[float, dict]] = []
    elapsed = 0.0
    for slide in slides:
        elapsed += slide["duration"]
        cumulative.append((elapsed, slide))

    def slide_at(timestamp: float) -> dict:
        for end, slide in cumulative:
            if timestamp <= end:
                return slide
        return slides[-1]

    frame_count = math.ceil(elapsed * fps)
    for frame in range(frame_count):
        slide = slide_at(frame / fps)
        svg = render_fzf(slide) if slide["kind"] == "fzf" else render_terminal(slide)
        svg_path = svg_dir / f"frame_{frame:04d}.svg"
        png_path = frames_dir / f"frame_{frame:04d}.png"
        svg_path.write_text(svg, encoding="utf-8")
        subprocess.run(["rsvg-convert", "-w", str(GIF_WIDTH), "-h", str(GIF_HEIGHT), str(svg_path), "-o", str(png_path)], check=True)

    output.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(frames_dir / "frame_%04d.png"),
            "-vf",
            "fps="
            + str(fps)
            + ",split[s0][s1];[s0]palettegen=max_colors=96[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5",
            "-loop",
            "0",
            str(output),
        ]
    )


def scan_gif_for_private_strings(output: Path) -> None:
    data = output.read_bytes()
    needles = [b"/Users", b"token", b"secret", b"auth", b"google/", b"openai/", b"ollama-cloud/", b"deepseek/", b"minimax-"]
    found = [needle.decode("utf-8", errors="ignore") for needle in needles if needle in data]
    if found:
        raise SystemExit(f"Generated GIF contains suspicious strings: {', '.join(found)}")


def main() -> int:
    args = parse_args()
    require_tool("rsvg-convert")
    require_tool("ffmpeg")
    require_tool(args.opencode)

    tmp_root = Path(args.tmp_root) if args.tmp_root else Path(tempfile.mkdtemp(prefix="agentic-tui-gif."))
    tmp_root.mkdir(parents=True, exist_ok=True)
    project_dir = tmp_root / "project"
    demo_home = tmp_root / "home"
    demo_home.mkdir(parents=True, exist_ok=True)

    copy_opencode_state(Path.home(), demo_home)
    print(f"[gif] temp root: {tmp_root}")
    print("[gif] running agentic TUI with deterministic fzf selections")
    run_agentic_tui(args, tmp_root, project_dir, demo_home)

    mappings = read_mappings(project_dir)
    print("[gif] mapped roles:")
    for role, model, fallback in mappings:
        print(f"[gif]   {role}: main={model} fallback={fallback}")

    if args.skip_opencode:
        print("[gif] using built-in OpenCode output sample (--skip-opencode)")
    else:
        print("[gif] running OpenCode product-owner")
    opencode_output = run_opencode(args, tmp_root, project_dir, demo_home)
    opencode_lines = clean_opencode_output(opencode_output)
    if not args.skip_opencode and not any(line.startswith("> product-owner") for line in opencode_lines):
        raise SystemExit(f"OpenCode output did not include product-owner header; see {opencode_output}")

    output = Path(args.output)
    print(f"[gif] rendering {output}")
    slides = build_slides(args, mappings, opencode_lines)
    render_gif(slides, output, tmp_root, args.fps)
    scan_gif_for_private_strings(output)
    print(f"[gif] wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
