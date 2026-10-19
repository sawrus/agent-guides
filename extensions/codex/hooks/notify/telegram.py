#!/usr/bin/env python3
"""Telegram notifications for Claude Code, Codex and OpenCode.

Claude and Codex call this script from native hooks; the OpenCode plugin pipes
its session events here. It reads one payload (JSON) from stdin, prints `{}` and
always exits 0. The network call runs in a detached child so the agent never
waits for Telegram. Agent Markdown is rendered as Telegram HTML; when Telegram
rejects the markup, the same message is resent as plain text.
"""
import argparse
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

# The helper is imported from the user's project; bytecode there would be an untracked
# `.agent/notify/__pycache__` that uninstall leaves behind.
sys.dont_write_bytecode = True
try:
    import telegram_turn
except ImportError:  # partial install: send without the agent line and never mark the turn final
    telegram_turn = None

MAX_PAYLOAD = 131072
TELEGRAM_LIMIT = 4096
PREVIEW_LIMIT = 3000
OFF = {'0', 'false', 'no', 'n', 'off'}
HOSTS = {'claude': 'Claude Code', 'codex': 'Codex', 'opencode': 'OpenCode'}
LABEL_LIMIT = 64
KINDS = {'final': ('✅', 'Задача завершена'), 'interim': ('💬', 'Промежуточный ответ'),
         'waiting': ('⏳', 'Ожидает ввода')}


def read_json(path, default=None):
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
            return default
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def enabled(project):
    if os.environ.get('AGENTIC_TELEGRAM', '').lower() in OFF:
        return False
    settings = (read_json(project / '.agentic.json', {}) or {}).get('settings') or {}
    current = ((settings.get('notifications') or {}).get('telegram') or {}).get('enabled')
    if isinstance(current, bool):
        return current
    legacy = ((settings.get('opencode_plugins') or {}).get('telegram') or {}).get('enabled')
    return legacy is True


def credentials():
    base = os.environ.get('AGENTIC_CONFIG_DIR')
    directory = Path(base) if base else Path(os.environ.get('HOME') or Path.home()) / '.config' / 'agentic'
    config = read_json(directory / 'config.json', {}) or {}
    for section in ((config.get('notifications') or {}).get('telegram'),
                    ((config.get('opencode') or {}).get('plugins') or {}).get('telegram')):
        if isinstance(section, dict) and section.get('botToken') and section.get('chatId'):
            return str(section['botToken']), str(section['chatId'])
    return None, None


def api_base():
    return (os.environ.get('AGENTIC_TELEGRAM_API_BASE_URL')
            or os.environ.get('OPENCODE_TELEGRAM_API_BASE_URL')
            or 'https://api.telegram.org').rstrip('/')


def redact(text, secrets):
    text = str(text)
    for secret in secrets:
        if secret:
            text = text.replace(secret, '[redacted]')
    return text


def log(project, message, secrets):
    try:
        directory = project / '.agentic'
        if directory.is_symlink():
            return
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / 'telegram-debug.log'
        if path.is_symlink():
            return
        with path.open('a', encoding='utf-8') as handle:
            handle.write(time.strftime('%Y-%m-%dT%H:%M:%S ') + redact(message, secrets) + '\n')
    except OSError:
        pass


def text_blocks(content):
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [block.get('text', '') for block in content
                if isinstance(block, dict) and block.get('type') == 'text' and block.get('text')]
    return []


def transcript_reply(raw):
    """Assistant text after the last real user message in a Claude JSONL transcript."""
    if not isinstance(raw, str) or not raw:
        return ''
    path = Path(raw).expanduser()
    try:
        if path.is_symlink() or not path.is_file():
            return ''
        size = path.stat().st_size
        with path.open('rb') as handle:
            handle.seek(max(0, size - 2_000_000))
            lines = handle.read().decode('utf-8', 'replace').splitlines()
    except OSError:
        return ''
    parts = []
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        message = entry.get('message') or {}
        if entry.get('type') == 'assistant':
            parts[:0] = text_blocks(message.get('content'))
        elif entry.get('type') == 'user' and text_blocks(message.get('content')):
            break
    return '\n'.join(part for part in parts if part).strip()


def esc(text):
    return html.escape(str(text), quote=False)


def inline(text):
    """Inline Markdown -> Telegram HTML. Code spans and links are protected from other rules."""
    saved = []

    def keep(fragment):
        saved.append(fragment)
        return f'\x00{len(saved) - 1}\x00'

    text = re.sub(r'`([^`\n]+)`', lambda m: keep(f'<code>{esc(m.group(1))}</code>'), text)

    def link(match):
        label, target = match.group(1), match.group(2)
        if re.match(r'https?://', target):
            return keep(f'<a href="{html.escape(target)}">{esc(label)}</a>')
        # Telegram cannot open project-relative paths; show the path instead.
        return keep(f'{esc(label)} (<code>{esc(target)}</code>)')

    text = re.sub(r'\[([^\]\n]+)\]\(([^)\s]+)\)', link, text)
    text = esc(text)
    text = re.sub(r'\*\*(.+?)\*\*|__(.+?)__', lambda m: f'<b>{m.group(1) or m.group(2)}</b>', text)
    text = re.sub(r'(?<![\w*])\*(?![\s*])(.+?)(?<![\s*])\*(?![\w*])', r'<i>\1</i>', text)
    text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text)
    return re.sub('\x00(\\d+)\x00', lambda m: saved[int(m.group(1))], text)


def table(rows):
    """Markdown table -> aligned monospace block (Telegram has no table markup)."""
    cells = [[c.strip().replace('`', '').replace('**', '') for c in row.strip().strip('|').split('|')]
             for row in rows if not re.match(r'^\s*\|?[\s:|-]+\|?\s*$', row)]
    width = max(len(r) for r in cells)
    cells = [r + [''] * (width - len(r)) for r in cells]
    sizes = [max(len(r[i]) for r in cells) for i in range(width)]
    lines = [' │ '.join(c.ljust(sizes[i]) for i, c in enumerate(r)).rstrip() for r in cells]
    if len(lines) > 1:
        lines.insert(1, '─┼─'.join('─' * n for n in sizes))
    return f'<pre>{esc(chr(10).join(lines))}</pre>'


def markdown_html(text):
    """Render the Markdown subset agents write (fences, headings, lists, quotes, tables)."""
    lines = text.replace('\r\n', '\n').split('\n')
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        fence = re.match(r'^\s*(```|~~~)\s*([\w+#.-]*)', line)
        if fence:
            body, i = [], i + 1
            while i < len(lines) and not lines[i].strip().startswith(fence.group(1)):
                body.append(lines[i])
                i += 1
            language = f' class="language-{esc(fence.group(2))}"' if fence.group(2) else ''
            out.append(f'<pre><code{language}>{esc(chr(10).join(body))}</code></pre>')
            i += 1
            continue
        if line.lstrip().startswith('|'):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith('|'):
                rows.append(lines[i])
                i += 1
            out.append(table(rows))
            continue
        if line.lstrip().startswith('>'):
            quoted = []
            while i < len(lines) and lines[i].lstrip().startswith('>'):
                quoted.append(inline(lines[i].lstrip()[1:].strip()))
                i += 1
            out.append(f'<blockquote>{chr(10).join(quoted)}</blockquote>')
            continue
        heading = re.match(r'^\s*#{1,6}\s+(.*?)\s*#*\s*$', line)
        bullet = re.match(r'^(\s*)[-*+]\s+(.*)$', line)
        if heading:
            out.append(f'<b>{inline(heading.group(1))}</b>')
        elif re.match(r'^\s*([-*_])(\s*\1){2,}\s*$', line):
            out.append('')
        elif bullet:
            out.append(f'{"  " * (len(bullet.group(1)) // 2)}• {inline(bullet.group(2))}')
        else:
            out.append(inline(line))
        i += 1
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(out)).strip()


def plain(text):
    """Fallback text when Telegram rejects the HTML markup."""
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def preview(text, limit):
    """Cut Markdown at a paragraph or line boundary and close an open code fence."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    boundary = max(cut.rfind('\n\n'), cut.rfind('\n'))
    cut = cut[:boundary] if boundary > limit // 2 else cut
    if cut.count('```') % 2:
        cut += '\n```'
    return cut.rstrip() + '\n…'


def facts(project, host, payload, with_final):
    """Agent, model and final flag of the turn; unknown values degrade to an interim message."""
    unknown = {'agent': None, 'model': None, 'final': False}
    if telegram_turn is None:
        return unknown
    try:
        return telegram_turn.turn_facts(host, payload, project, read_json, with_final)
    except Exception as error:  # noqa: BLE001 - a broken fact source must not drop the message
        log(project, f'telegram turn facts failed: {error}', credentials())
        return unknown


def header(kind, where, turn, title=None):
    """Return (html, plain) header lines: kind and place, then `🤖 agent · model`, then the title."""
    mark, label = KINDS[kind]
    rich, text = [f'{mark} <b>{label}</b> — {esc(where)}'], [f'{mark} {label} — {where}']
    who = ' · '.join(str(part)[:LABEL_LIMIT] for part in (turn.get('agent'), turn.get('model')) if part)
    if who:
        rich.append(f'🤖 {esc(who)}')
        text.append(f'🤖 {who}')
    if isinstance(title, str) and title.strip():
        rich.append(f'<i>{inline(title.strip())}</i>')
        text.append(title.strip())
    return '\n'.join(rich), '\n'.join(text)


def waiting_body(project, host, where, payload):
    detail = payload.get('message') or payload.get('tool_name') or 'нужно действие пользователя'
    tool_input = payload.get('tool_input')
    command = tool_input.get('command') if isinstance(tool_input, dict) else None
    body = f'{detail}\n```\n{command}\n```' if isinstance(command, str) else str(detail)
    return (*header('waiting', where, facts(project, host, payload, False)), body)


def stop_body(project, host, where, payload):
    reply = payload.get('last_assistant_message')
    if not isinstance(reply, str) or not reply.strip():
        reply = transcript_reply(payload.get('transcript_path'))
    turn = facts(project, host, payload, True)
    kind = 'final' if turn.get('final') is True else 'interim'
    return (*header(kind, where, turn, payload.get('title')), (reply or '').strip())


def skipped(event, payload):
    """A Stop hook re-entered by its own continuation must not notify again."""
    return event == 'stop' and bool(payload.get('stop_hook_active'))


def build(project, host, event, payload):
    """Return (header_html, header_plain, body_markdown) or None when nothing should be sent."""
    where = f'{project.name or "project"} · {HOSTS.get(host, host)}'
    if event == 'waiting':
        return waiting_body(project, host, where, payload)
    if skipped(event, payload):
        return None
    return stop_body(project, host, where, payload)


def post(url, data, headers):
    request = urllib.request.Request(url, data, headers)
    with urllib.request.urlopen(request, timeout=15) as response:
        response.read(65536)


def send_message(base, chat, rich, fallback):
    """Send HTML; on a markup rejection (HTTP 400) resend plain text. Returns the Telegram error, if any."""
    def message(text, mode=None):
        payload = {'chat_id': chat, 'text': text[:TELEGRAM_LIMIT], 'disable_web_page_preview': True}
        if mode:
            payload['parse_mode'] = mode
        post(base + '/sendMessage', json.dumps(payload).encode(), {'Content-Type': 'application/json'})

    if len(rich) <= TELEGRAM_LIMIT:
        try:
            message(rich, 'HTML')
            return None
        except urllib.error.HTTPError as error:
            if error.code != 400:
                raise
            reason = error.read(512).decode('utf-8', 'replace')
    else:
        reason = f'rendered HTML exceeds {TELEGRAM_LIMIT} characters'
    message(fallback)
    return reason


def send(project, message, session):
    header_html, header_plain, body = message
    token, chat = credentials()
    secrets = (token, chat)
    if not token or not chat:
        log(project, 'telegram credentials missing; notification skipped', secrets)
        return
    base = f'{api_base()}/bot{token}'
    try:
        if len(body) >= TELEGRAM_LIMIT:
            boundary = uuid.uuid4().hex
            filename = f"response-{(session or 'session')[:8]}.md"
            form = (f'--{boundary}\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n{chat}\r\n'
                    f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="{filename}"\r\n'
                    'Content-Type: text/markdown\r\n\r\n').encode() + body.encode() + f'\r\n--{boundary}--\r\n'.encode()
            post(base + '/sendDocument', form, {'Content-Type': f'multipart/form-data; boundary={boundary}'})
            note = f'Полный ответ во вложении ({len(body)} символов).'
            header_html, header_plain = f'{header_html}\n<i>{note}</i>', f'{header_plain}\n{note}'
            body = preview(body, PREVIEW_LIMIT)
        rich = f'{header_html}\n\n{markdown_html(body)}' if body else header_html
        fallback = f'{header_plain}\n\n{plain(body)}' if body else header_plain
        rejected = send_message(base, chat, rich, fallback)
        if rejected:
            log(project, f'telegram markup not used, sent plain text: {rejected}', secrets)
    except Exception as error:  # noqa: BLE001 - notification failures must never surface to the agent
        log(project, f'telegram send failed: {error}', secrets)


def detach(args, project, raw):
    """Hand the payload to a detached `--sync` child so the agent never waits for the scan or Telegram."""
    child = subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), '--host', args.host, '--event', args.event,
         '--project-dir', str(project), '--sync'],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True)
    child.stdin.write(raw.encode('utf-8'))
    child.stdin.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', choices=tuple(HOSTS), required=True)
    parser.add_argument('--event', choices=('stop', 'waiting'), required=True)
    parser.add_argument('--project-dir', default='.')
    parser.add_argument('--sync', action='store_true', help='send in this process (tests and the detached child)')
    args = parser.parse_args()
    project = Path(args.project_dir).resolve()
    try:
        raw = sys.stdin.read(MAX_PAYLOAD + 1)
        payload = json.loads(raw) if raw.strip() and len(raw) <= MAX_PAYLOAD else {}
        if not isinstance(payload, dict):
            payload = {}
        if enabled(project) and not skipped(args.event, payload):
            if not args.sync:
                detach(args, project, raw)
            elif message := build(project, args.host, args.event, payload):
                send(project, message, str(payload.get('session_id') or ''))
    except Exception as error:  # noqa: BLE001
        log(project, f'telegram hook error: {error}', credentials())
    if not args.sync:
        print('{}')


if __name__ == '__main__':
    main()
