"""Turn facts for the Telegram header: agent, model and whether the turn is final.

The notifier imports this module only in its detached `--sync` child, so the
transcript scan never delays the agent. Every source is local host data; there
are no network calls. When the evidence is missing or unclear, the turn is
reported as interim: a missing "done" mark is better than a repeated one.
See docs/notifications/telegram-header/notes.md for the per-host rules.
"""
import json
from pathlib import Path
import re

SCAN_LIMIT = 64 * 1024 * 1024
TERMINAL_STATUSES = frozenset({'completed', 'failed', 'killed', 'stopped', 'cancelled', 'error'})
# A subagent that still runs its own background work reports "completed" too early.
INTERIM_NOTE = 'background work of its own still running'
# The launch texts keep text-only launch results (no `toolUseResult`) in the scan; without them
# such a launch is never seen and the turn is wrongly final.
CLAUDE_MARKERS = (b'"assistant"', b'toolUseResult', b'<task-notification>', b'agent-setting',
                  b'Async agent launched', b'Command running in background with ID')
CODEX_MARKERS = (b'spawn_agent', b'followup_task', b'FINAL_ANSWER')
CODEX_FINAL = 'Message Type: FINAL_ANSWER'
# An unkeyed child can never be matched to its answer, so it keeps the turn interim.
CODEX_UNKEYED = '?unkeyed'
CLAUDE_SETTINGS = ('.claude/settings.local.json', '.claude/settings.json')
NOTIFICATION = re.compile(r'<task-notification>(.*?)</task-notification>', re.S)
TEXT_LAUNCHES = (re.compile(r'Async agent launched.*?agentId: (\w+)', re.S),
                 re.compile(r'Command running in background with ID: (\w+)'))


def turn_facts(host, payload, project, read_json, with_final):
    """Return {'agent', 'model', 'final'}; `final` is False unless `with_final` is set."""
    if host == 'claude':
        facts = claude_facts(payload, project, read_json, with_final)
    elif host == 'codex':
        facts = codex_facts(payload, with_final)
    else:
        facts = opencode_facts(payload)
    facts['final'] = bool(with_final and facts.get('final') is True)
    return facts


def as_dict(value):
    """Valid JSON can still have an unexpected shape; such a field counts as empty."""
    return value if isinstance(value, dict) else {}


def text_value(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def model_label(value):
    """`{'id': 'x'}` or `provider/x#variant` -> `x`."""
    if isinstance(value, dict):
        return text_value(value.get('id')) or text_value(value.get('modelID'))
    label = text_value(value)
    if not label:
        return None
    return text_value(label.rsplit('/', 1)[-1].split('#', 1)[0])


def own_agent(payload):
    """`agent_type` names the main session only when no `agent_id` marks a subagent."""
    return None if payload.get('agent_id') else text_value(payload.get('agent_type'))


def parse_line(line):
    try:
        entry = json.loads(line)
    except ValueError:
        return None
    return entry if isinstance(entry, dict) else None


def transcript_entries(raw_path, markers):
    """Entries from lines that contain a marker; None when the file is missing, unsafe or too large."""
    if not isinstance(raw_path, str) or not raw_path:
        return None
    path = Path(raw_path).expanduser()
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > SCAN_LIMIT:
            return None
        entries, total = [], 0
        with path.open('rb') as handle:
            for line in handle:
                total += len(line)
                if total > SCAN_LIMIT:
                    return None
                entry = parse_line(line) if any(marker in line for marker in markers) else None
                if entry is not None:
                    entries.append(entry)
        return entries
    except OSError:
        return None


def main_thread(entries):
    return [entry for entry in entries or [] if entry.get('isSidechain') is not True
            and not str(entry.get('type', '')).startswith('api-request')]


# --- Claude Code -------------------------------------------------------------

def claude_facts(payload, project, read_json, with_final):
    entries = transcript_entries(payload.get('transcript_path'), CLAUDE_MARKERS)
    thread = main_thread(entries)
    return {'agent': claude_agent(payload, thread, project, read_json),
            'model': claude_model(thread),
            'final': with_final and claude_final(payload, entries, thread)}


def claude_agent(payload, thread, project, read_json):
    agent = own_agent(payload)
    if agent:
        return agent
    for entry in reversed(thread):
        if entry.get('type') == 'agent-setting' and text_value(entry.get('agentSetting')):
            return text_value(entry.get('agentSetting'))
    for rel in CLAUDE_SETTINGS:
        settings = read_json(project / rel, {})
        if isinstance(settings, dict) and text_value(settings.get('agent')):
            return text_value(settings.get('agent'))
    return None


def claude_model(thread):
    for entry in reversed(thread):
        message = entry.get('message') if entry.get('type') == 'assistant' else None
        model = message.get('model') if isinstance(message, dict) else None
        if isinstance(model, str) and model and not model.startswith('<'):
            return model_label(model)
    return None


def claude_final(payload, entries, thread):
    tasks, crons = payload.get('background_tasks'), payload.get('session_crons')
    if (isinstance(crons, list) and crons) or (isinstance(tasks, list) and tasks):
        return False
    if entries is None:
        # Without a transcript, only the host's own empty task list proves the turn is final.
        return isinstance(tasks, list)
    pending, still_running = claude_pending_state(thread)
    if isinstance(tasks, list):
        # Here the host list is empty (a non-empty one returned above), so the host has no work
        # in flight. That settles ids whose last completion said "still running": the transcript
        # has no later event for them. Other ids stay pending, because the transcript also sees
        # launches (for example background Bash) that the list may omit.
        pending -= still_running
    return not pending


def claude_pending(thread):
    """Ids the main thread launched in the background and that have not finished yet."""
    return claude_pending_state(thread)[0]


def claude_pending_state(thread):
    """(pending ids, pending ids whose last completion had the interim note)."""
    pending, still_running = set(), set()
    for entry in thread:
        launched = launched_ids(entry)
        pending.update(launched)
        still_running.difference_update(launched)
        for task_id, status, interim in delivered_notifications(entry):
            if task_id not in pending or status not in TERMINAL_STATUSES:
                continue
            if interim:
                still_running.add(task_id)
            else:
                pending.discard(task_id)
                still_running.discard(task_id)
    return pending, still_running


def tool_result_texts(content):
    texts = []
    for block in content if isinstance(content, list) else []:
        inner = block.get('content') if isinstance(block, dict) and block.get('type') == 'tool_result' else None
        if isinstance(inner, str):
            texts.append(inner)
        elif isinstance(inner, list):
            texts.extend(part.get('text', '') for part in inner if isinstance(part, dict))
    return texts


def launched_ids(entry):
    if entry.get('type') != 'user':
        return []
    result = entry.get('toolUseResult')
    if isinstance(result, dict):
        ids = [result.get('backgroundTaskId'), result.get('resumedAgentId')]
        if result.get('status') == 'async_launched' or result.get('isAsync') is True:
            ids.append(result.get('agentId'))
        return [value for value in ids if isinstance(value, str) and value]
    texts = tool_result_texts(as_dict(entry.get('message')).get('content'))
    return [match for text in texts if isinstance(text, str)
            for pattern in TEXT_LAUNCHES for match in pattern.findall(text)]


def delivered_notifications(entry):
    """Notification blocks the model has actually received; queued copies do not count."""
    text = None
    if entry.get('type') == 'user':
        text = as_dict(entry.get('message')).get('content')
    elif entry.get('type') == 'attachment':
        attachment = as_dict(entry.get('attachment'))
        if attachment.get('type') == 'queued_command' and attachment.get('commandMode') == 'task-notification':
            text = attachment.get('prompt')
    if not isinstance(text, str):
        return []
    return [parse_notification(block) for block in NOTIFICATION.findall(text)]


def tag(block, name):
    match = re.search(rf'<{name}>(.*?)</{name}>', block, re.S)
    return match.group(1).strip() if match else ''


def parse_notification(block):
    """`<task-notification>` body -> (task_id, status, interim)."""
    return tag(block, 'task-id'), tag(block, 'status').lower(), INTERIM_NOTE in tag(block, 'note')


# --- Codex -------------------------------------------------------------------

def codex_facts(payload, with_final):
    final = False
    if with_final:
        entries = transcript_entries(payload.get('transcript_path'), CODEX_MARKERS)
        final = entries is not None and not codex_open_children(entries)
    return {'agent': own_agent(payload), 'model': model_label(payload.get('model')), 'final': final}


def last_segment(value):
    return value.rstrip('/').rsplit('/', 1)[-1] if isinstance(value, str) and value.strip('/') else None


def codex_item(entry):
    item = entry.get('payload') if entry.get('type') == 'response_item' else entry
    return item if isinstance(item, dict) else {}


def codex_opened(item):
    """Child key opened by a `spawn_agent` / `followup_task` call, or None."""
    name = str(item.get('name', '')).rsplit('.', 1)[-1]
    if item.get('type') != 'function_call' or name not in ('spawn_agent', 'followup_task'):
        return None
    arguments = item.get('arguments')
    if isinstance(arguments, str):
        arguments = parse_line(arguments) or {}
    if not isinstance(arguments, dict):
        arguments = {}
    return last_segment(arguments.get('task_name' if name == 'spawn_agent' else 'target')) or CODEX_UNKEYED


def message_texts(content):
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [part.get('text', '') for part in content if isinstance(part, dict)]
    return []


def codex_closed(item):
    if item.get('type') != 'agent_message':
        return None
    if any(isinstance(text, str) and CODEX_FINAL in text for text in message_texts(item.get('content'))):
        return last_segment(item.get('author'))
    return None


def codex_open_children(entries):
    """Children whose last open is not followed by a FINAL_ANSWER from the same author."""
    state = {}
    for entry in entries:
        item = codex_item(entry)
        opened, closed = codex_opened(item), codex_closed(item)
        if opened:
            state[opened] = True
        if closed in state:
            state[closed] = False
    return {key for key, is_open in state.items() if is_open}


# --- OpenCode ----------------------------------------------------------------

def opencode_facts(payload):
    """The plugin tracks child sessions; only an explicit `final: true` counts."""
    return {'agent': text_value(payload.get('agent')), 'model': model_label(payload.get('model')),
            'final': payload.get('final') is True}
