#!/usr/bin/env python3
"""Generate images/how_to_use_agentic.gif from real runs only.

Part 1 drives the real `agentic tui` in a pseudo-terminal with real key presses and renders the emulated screen
after every key (requires `pyte`). It installs the default lean profile and a demo company rule. Part 2 shows the
same prompt answered by the native main session of Codex, Claude Code and OpenCode in the installed project.
Paid: three short host runs. `--reuse` re-renders saved outputs without calls.

Usage (pyte lives in a venv outside the repository):
    python3 -m venv /tmp/agentic-tui-venv && /tmp/agentic-tui-venv/bin/pip install pyte pillow
    make build && /tmp/agentic-tui-venv/bin/python scripts/generate_how_to_use_agentic_gif.py --work /tmp/agentic-gif
"""
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import textwrap

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 960, 596
DISPLAY_DIR = "~/demo"
PROMPT = "Define acceptance criteria for a tiny CLI that greets a user by name. Answer with at most 4 short numbered points."
HOSTS = [
    ("codex", "Codex", "CX"),
    ("claude", "Claude Code", "CC"),
    ("opencode", "OpenCode", "OC"),
]
CONFIG_ONLY = ["Antigravity", "Gemini", "Cursor", "Kilocode"]
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
COLORS = {"bg": "#0d1117", "bar": "#161b22", "border": "#30363d", "normal": "#d6deeb", "dim": "#8b98a7", "cmd": "#79c0ff",
          "ok": "#7ee787", "warn": "#f2cc60", "section": "#d2a8ff", "title": "#ffffff", "agent": "#56d4dd"}


DOWN, ENTER, SPACE, PROJECT = "\x1b[B", "\r", " ", "<project path>"
MODELS = {"codex": "gpt-6.1-terra", "claude": "sonnet", "opencode": "openai/gpt-6.1-terra"}
# A demo company rule, typed into the "Company rules" step as a path relative to the project.
COMPANY_DIR = "../company-rules"
COMPANY_RULE = """---
description: Release notes for every user-visible change.
paths:
  - "CHANGELOG.md"
---

# Release notes

- Add one line under the new version in `CHANGELOG.md` for every user-visible change.
- Name the ticket id in the line.
"""
# The real installer flow as screens: (keys pressed on this screen, label). Every key press becomes one frame.
TUI_SCREENS = [
    ([DOWN, ENTER], "theme: dark"),
    ([PROJECT, ENTER], "target project"),
    ([SPACE, DOWN, SPACE, DOWN, SPACE, ENTER], "agents: opencode, codex, claude"),
    ([ENTER], "claude: lean profile (default)"),
    ([ENTER], "codex: lean profile (default)"),
    ([ENTER], "opencode: lean profile (default)"),
    ([DOWN] * 6 + [SPACE, ENTER], "integrations: context7"),
    ([SPACE, DOWN, SPACE, ENTER], "areas: devops, software"),
    ([DOWN] * 3 + [SPACE, ENTER], "devops: infrastructure"),
    ([SPACE] + [DOWN] * 3 + [SPACE, ENTER], "software: backend, general"),
    (list(COMPANY_DIR) + [ENTER], "company rules: directory"),
    ([ENTER], "company rules: no repository"),
    ([ENTER], "OpenCode plugins: none"),
    ([ENTER], "Claude model profile"),
    ([ENTER], "Context7 without key"),
]
HOLD_MS = {DOWN: 220, SPACE: 650, ENTER: 1100}
COLS, ROWS, CELL_W, CELL_H = 104, 30, 9, 18
TERM_COLORS = {"black": "#0d1117", "red": "#ff7b72", "green": "#7ee787", "yellow": "#f2cc60", "blue": "#79c0ff",
               "magenta": "#d2a8ff", "cyan": "#56d4dd", "white": "#e6edf3", "brightblack": "#8b949e", "default": "#d6deeb"}


def record_tui(agentic: str, work: Path, project: Path) -> list[tuple[Image.Image, int]]:
    """Real key presses into the real TUI; one rendered frame per resulting screen."""
    import fcntl, pty, select, struct, termios, time as clock
    import pyte
    home = work / "tui-home"
    shutil.rmtree(home, ignore_errors=True)
    home.mkdir(parents=True)
    company = (project / COMPANY_DIR / "software").resolve()
    company.mkdir(parents=True, exist_ok=True)
    (company / "release-notes.md").write_text(COMPANY_RULE, encoding="utf-8")
    screen = pyte.Screen(COLS, ROWS)
    stream = pyte.ByteStream(screen)
    raw = bytearray()
    pid, fd = pty.fork()
    if pid == 0:
        env = {**os.environ, "HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"), "TERM": "xterm-256color",
               "AGENTIC_DOCTOR": "0", "AGENTIC_MEMPALACE_SETUP": "skip", "AGENTIC_TELEGRAM": "off"}
        os.chdir(work)
        os.execve(agentic, [agentic, "tui"], env)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))

    def pump(seconds: float) -> None:
        end = clock.time() + seconds
        while clock.time() < end:
            ready, _, _ = select.select([fd], [], [], 0.03)
            if ready:
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    return
                raw.extend(chunk)
                stream.feed(chunk)

    frames = []
    pump(2.0)
    frames.append((render_screen(screen, "agentic tui"), 1600))
    for keys, label in TUI_SCREENS:
        for key in keys:
            typed = list(str(project)) if key == PROJECT else [key]
            for part in typed:
                os.write(fd, part.encode())
                pump(0.6 if part == ENTER else 0.12)
                frames.append((render_screen(screen, f"agentic tui · {label}"), HOLD_MS.get(part, 70)))
    pump(3.0)
    os.kill(pid, 9)
    if not (project / ".agentic.json").is_file():
        raise SystemExit("TUI did not finish the installation; inspect the last frames")
    # The installer leaves the alternate screen when it finishes; its own log file holds the final report.
    log = re.search(rb"Agentic log file: (\S+)", raw)
    report = Path(log[1].decode()).read_text(encoding="utf-8", errors="replace") if log else ""
    return frames, report


def color(value: str, fallback: str) -> str:
    if value in TERM_COLORS:
        return TERM_COLORS[value]
    if value.startswith("bright") and value[6:] in TERM_COLORS:
        return TERM_COLORS[value[6:]]
    return "#" + value if re.fullmatch(r"[0-9a-fA-F]{6}", value or "") else fallback


def render_screen(screen, title: str) -> Image.Image:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 14)
    bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 14)
    image = Image.new("RGB", (COLS * CELL_W + 24, ROWS * CELL_H + 56), COLORS["bg"])
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, image.width, 34], fill=COLORS["bar"])
    for index, dot in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        draw.ellipse([14 + index * 20, 11, 26 + index * 20, 23], fill=dot)
    draw.text((84, 9), title, fill=COLORS["dim"], font=font)
    for row in range(ROWS):
        line = screen.buffer[row]
        for col in range(COLS):
            char = line[col]
            fg = COLORS["normal"] if char.fg == "default" else color(char.fg, COLORS["normal"])
            bg = COLORS["bg"] if char.bg == "default" else color(char.bg, COLORS["bg"])
            if char.reverse:
                fg, bg = bg, fg
            x, y = 12 + col * CELL_W, 44 + row * CELL_H
            if bg != COLORS["bg"]:
                draw.rectangle([x, y, x + CELL_W, y + CELL_H], fill=bg)
            if char.data.strip():
                draw.text((x, y), char.data, fill=fg, font=bold if char.bold else font)
    return image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(ROOT / "images/how_to_use_agentic.gif"))
    parser.add_argument("--work", help="Working directory for the demo project and captured outputs")
    parser.add_argument("--reuse", action="store_true", help="Render from outputs already captured in --work")
    parser.add_argument("--agentic", default=str(ROOT / "target/debug/agentic"))
    parser.add_argument("--hosts", default="codex,claude,opencode", help="Hosts to (re)capture; others reuse saved output")
    return parser.parse_args()


def scrub(text: str, project: Path) -> str:
    text = ANSI.sub("", text).replace(str(project), DISPLAY_DIR).replace(str(Path.home()), "~")
    return text.replace("—", "-")


def host_run(host: str, project: Path, out: Path) -> None:
    """One short real answer of the native main session per host (lean profile); raw output is kept for re-rendering."""
    # OpenCode resolves the project from PWD, which Popen(cwd=...) does not update.
    env = {**os.environ, "AGENTIC_TELEGRAM": "off", "PWD": str(project)}
    for name in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SSE_PORT", "CLAUDE_PROJECT_DIR", "CLAUDE_CODE_SESSION_ID",
                 "CLAUDE_CODE_SESSION_ACCESS_TOKEN", "CODEX_THREAD_ID", "CODEX_SESSION_ID"):
        env.pop(name, None)
    if host == "codex":
        command = ["codex", "exec", "--json", "--skip-git-repo-check", "--sandbox", "read-only", "-m", MODELS[host],
                   "-C", str(project), PROMPT]
    elif host == "claude":
        command = ["claude", "-p", "--model", MODELS[host], "--output-format", "json", PROMPT]
    else:
        command = ["opencode", "run", "--standalone", "--model", MODELS[host], "--format", "json", PROMPT]
    process = subprocess.Popen(command, cwd=project, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        stdout, _ = process.communicate(timeout=300)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, 9)
        stdout, _ = process.communicate()
    out.write_text(stdout or "", encoding="utf-8")


def answer(host: str, raw: str) -> tuple[str, str]:
    """(model, final answer text) parsed from each host's machine-readable output."""
    model, text = "", ""
    for line in raw.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if host == "codex" and event.get("type") == "item.completed" and (event.get("item") or {}).get("type") == "agent_message":
            text = event["item"].get("text", "")
        if host == "claude" and event.get("type") == "result":
            text = event.get("result", "")
            model = next(iter(event.get("modelUsage") or {}), "")
        if host == "opencode" and (event.get("part") or {}).get("type") == "text":
            text = event["part"].get("text", "")
    if host != "claude" or not model:
        model = MODELS[host]
    return model, text.strip()


def text_node(x: int, y: int, text: str, style: str = "normal", size: int = 14, weight: str | None = None) -> str:
    weight = weight or ("700" if style in {"title", "section", "agent"} else "400")
    return (f'<text x="{x}" y="{y}" fill="{COLORS.get(style, COLORS["normal"])}" font-family="DejaVu Sans Mono, Menlo, monospace" '
            f'font-size="{size}" font-weight="{weight}" xml:space="preserve">{html.escape(text)}</text>')


def frame(title: str, rows: list[tuple[str, str]]) -> str:
    nodes, y = [], 64
    for style, line in rows[-26:]:
        nodes.append(text_node(20, y, line, style))
        y += 18
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}">'
            f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{COLORS["bg"]}"/><rect width="{WIDTH}" height="36" fill="{COLORS["bar"]}"/>'
            '<circle cx="20" cy="18" r="6" fill="#ff5f57"/><circle cx="40" cy="18" r="6" fill="#febc2e"/><circle cx="60" cy="18" r="6" fill="#28c840"/>'
            f'{text_node(82, 23, title, "dim", 13)}<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" fill="none" stroke="{COLORS["border"]}"/>'
            f'{"".join(nodes)}</svg>')


def wrap(style: str, text: str, width: int = 84) -> list[tuple[str, str]]:
    rows = []
    for line in text.splitlines() or [""]:
        for part in textwrap.wrap(line, width=width) or [""]:
            rows.append((style, part))
    return rows


def slides(work: Path, project: Path, report: str) -> list[tuple[float, str, list[tuple[str, str]]]]:
    lines = [re.sub(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ", "", line) for line in scrub(report, project).splitlines()]
    section = lines[next((i for i, l in enumerate(lines) if "Installation report" in l), 0):]
    section = section[:next((i for i, l in enumerate(section) if "Changelog" in l), len(section))]
    private = ("Changed paths report", "Knowledge base repo", "Config file", "JSON config file")
    shown = [l for l in section if l.strip() and not l.startswith(private)][:22]
    out_report = [(5.0, "agentic tui · installation report", [("section" if "===" in l else "ok", l) for l in shown])]
    tree = []
    for folder, label in ((".codex/agents", "Codex"), (".claude/agents", "Claude Code"), (".opencode/agents", "OpenCode")):
        helpers = sorted(p.stem for p in (project / folder).iterdir()) if (project / folder).is_dir() else []
        tree += [("agent", f"{folder}/  ({label}, lean)"), ("normal", "   " + ("  ".join(helpers) or "(none)"))]
    rules = sorted(p.stem for p in (project / ".agent/rules").rglob("*.md"))
    company = sorted(str(p.relative_to(project)) for p in (project / ".agent/company").rglob("*.md"))
    workflows = sorted(p.stem for p in (project / ".agent/workflows").glob("*.md"))
    out = [(5.0, "the same rules in every agent", [("section", "Installed by the TUI above"), ("normal", "")] + tree + [
        ("normal", ""), ("section", f"{len(rules)} rules in .agent/rules"), *wrap("dim", "  ".join(rules), 96)[:3],
        ("section", "Company rules"), *[("ok", "   " + path) for path in company[:3]],
        ("section", f"{len(workflows)} workflows in .agent/workflows"), *wrap("dim", "  ".join(workflows), 96)[:2],
        ("section", "Quality gate"), ("dim", "   make test + make lint on stop · acceptance in .agentic/gate/last.json")])]
    for key, name, _ in HOSTS:
        model, text = answer(key, (work / f"{key}.out").read_text(encoding="utf-8"))
        rows = [("cmd", f"$ {key} … \"{PROMPT[:60]}…\""), ("normal", ""), ("agent", f"> main session · {name} · {model}")]
        rows += wrap("normal", scrub(text, project) or "(no answer captured)", 96)[:18]
        out.append((5.0, f"{name} · lean main session", rows))
    final = [("section", "Same rules, real runs"), ("normal", "")]
    final += [("ok", f"  ✓ {name}  - main session answered") for _, name, _ in HOSTS]
    final += [("normal", ""), ("warn", "  ○ " + " · ".join(CONFIG_ONLY) + "  - configs ship, not run here"),
              ("normal", ""), ("dim", "  npx @jetrabbits/agentic   ·   github.com/sawrus/agent-guides")]
    out.append((4.5, "agentic", final))
    return out_report + out


def render(tui_frames, slide_list, output: Path, work: Path) -> None:
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    size = tui_frames[0][0].size
    frames = [image for image, _ in tui_frames]
    durations = [ms for _, ms in tui_frames]
    for index, (seconds, title, rows) in enumerate(slide_list):
        svg, png = work / f"slide-{index}.svg", work / f"slide-{index}.png"
        svg.write_text(frame(title, rows), encoding="utf-8")
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={size[0]},{size[1]}",
                        f"--screenshot={png}", svg.as_uri()], check=True, capture_output=True, timeout=60)
        frames.append(Image.open(png).convert("RGB"))
        durations.append(int(seconds * 1000))
    palette = frames[0].quantize(colors=96, method=Image.Quantize.MEDIANCUT)
    quantized = [image.quantize(palette=palette) for image in frames]
    output.parent.mkdir(parents=True, exist_ok=True)
    quantized[0].save(output, save_all=True, append_images=quantized[1:], duration=durations, loop=0, optimize=True)


def main() -> int:
    args = parse_args()
    work = Path(args.work).resolve() if args.work else Path(tempfile.mkdtemp(prefix="agentic-gif."))
    if ROOT in work.parents or work == ROOT:
        # Hosts resolve the project root through parent repositories; a nested demo would load this repo's guidance.
        raise SystemExit("--work must be outside the agent-guides repository")
    work.mkdir(parents=True, exist_ok=True)
    project = work / "demo"
    if args.reuse and project.exists():
        print("[gif] re-recording the TUI into a scratch copy; host answers are reused", flush=True)
        tui_frames, report = record_tui(args.agentic, work, work / "demo-rerecord")
        project_for_tree = project
    else:
        shutil.rmtree(project, ignore_errors=True)
        print("[gif] recording the real agentic TUI", flush=True)
        tui_frames, report = record_tui(args.agentic, work, project)
        project_for_tree = project
        for key, name, _ in HOSTS:
            if key in args.hosts.split(","):
                print(f"[gif] {name}: main session run", flush=True)
                host_run(key, project, work / f"{key}.out")
    for key, name, _ in HOSTS:
        if not (work / f"{key}.out").exists() or not answer(key, (work / f"{key}.out").read_text(encoding="utf-8"))[1]:
            raise SystemExit(f"{name} produced no answer; see {work / (key + '.out')}")
    output = Path(args.output)
    render(tui_frames, slides(work, project_for_tree, report), output, work)
    data = output.read_bytes()
    leaks = [s for s in (str(Path.home()).encode(), b"secret") if s in data]
    if leaks:
        raise SystemExit(f"GIF contains private strings: {leaks}")
    print(f"[gif] wrote {output} ({len(data) // 1024} KB, {len(tui_frames)} TUI frames); work dir {work}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
