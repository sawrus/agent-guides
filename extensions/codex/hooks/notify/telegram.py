#!/usr/bin/env python3
"""Telegram notifications for native Claude Code and Codex hooks.

Reads one hook payload (JSON) from stdin, prints `{}` and always exits 0.
The network call runs in a detached child so the agent never waits for Telegram.
Message format matches the OpenCode telegram-notification plugin.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import uuid

MAX_PAYLOAD = 131072
TELEGRAM_LIMIT = 4096
PREVIEW_LIMIT = 3000
OFF = {'0', 'false', 'no', 'n', 'off'}


def read_json(path, default=None):
    try:
        if path.is_symlink() or path.stat().st_size > 2_000_000:
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


def build(project, host, event, payload):
    """Return (header, body) or None when nothing should be sent."""
    name = project.name or 'project'
    if event == 'waiting':
        detail = payload.get('message') or payload.get('tool_name') or 'нужно действие пользователя'
        tool_input = payload.get('tool_input')
        if isinstance(tool_input, dict) and isinstance(tool_input.get('command'), str):
            detail = f"{detail}: {tool_input['command']}"
        return f'⏳ Ожидает ввода — {name}', str(detail)
    if payload.get('stop_hook_active'):
        return None
    reply = payload.get('last_assistant_message')
    if not isinstance(reply, str) or not reply.strip():
        reply = transcript_reply(payload.get('transcript_path'))
    return f'✅ Задача завершена — {name}', (reply or '').strip()


def post(url, data, headers):
    request = urllib.request.Request(url, data, headers)
    with urllib.request.urlopen(request, timeout=15) as response:
        response.read(65536)


def send(project, header, body, session):
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
            text = f'{header}\n\nПолный ответ в attachment ({len(body)} символов):\n\n{body[:PREVIEW_LIMIT]}...'
        else:
            text = f'{header}\n\n{body}' if body else header
        post(base + '/sendMessage', json.dumps({'chat_id': chat, 'text': text[:TELEGRAM_LIMIT]}).encode(),
             {'Content-Type': 'application/json'})
    except Exception as error:  # noqa: BLE001 - notification failures must never surface to the agent
        log(project, f'telegram send failed: {error}', secrets)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', choices=('claude', 'codex'), required=True)
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
        if enabled(project):
            message = build(project, args.host, args.event, payload)
            if message and args.sync:
                send(project, message[0], message[1], str(payload.get('session_id') or ''))
            elif message:
                child = subprocess.Popen(
                    [sys.executable, os.path.abspath(__file__), '--host', args.host, '--event', args.event,
                     '--project-dir', str(project), '--sync'],
                    stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True)
                child.stdin.write(raw.encode('utf-8'))
                child.stdin.close()
    except Exception as error:  # noqa: BLE001
        log(project, f'telegram hook error: {error}', credentials())
    if not args.sync:
        print('{}')


if __name__ == '__main__':
    main()
