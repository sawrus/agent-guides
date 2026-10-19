#!/usr/bin/env python3
"""Codex and Claude Code hook adapters: translate native payloads to JEV events and decisions to hook output.

`core` is the hook.py module; adapters call `core.run_event` and `core.review_packet` through it.
"""
import json
from pathlib import Path
import re

import questions
import routing

VERSION = 2
TRANSCRIPT_LIMIT = 20_000_000
TRANSCRIPT_TAIL = 262144
CODEX_SPAWN_TOOLS = ('spawn_agent', 'Agent', 'functions.spawn_agent', 'collaboration.spawn_agent', 'collaborationspawn_agent')
CODEX_ENCRYPTED_PREFIX = 'gAAAA'
CLAUDE_AGENT_TOOLS = ('Agent', 'Task')
# Questions to the user and plan approval are dialogs, not permission boundaries: JEV must never answer them.
CLAUDE_DIALOG_TOOLS = ('AskUserQuestion', 'ExitPlanMode')
# Claude Code delivers subagent hand-backs and background task notifications through UserPromptSubmit;
# they continue the current task and must not replace the original request.
CLAUDE_HARNESS_PROMPT = re.compile(r'\s*(?:Another Claude session sent a message:\s*)?<(?:agent-message|task-notification)\b')
WORKFLOW_RESOURCES = r'\.agent/workflows/[\w-]+\.md|\.claude/commands/[\w-]+\.md'
CODEX_DELEGATION = ('Act as its declared initiator and coordinate delivery. Delegate repository exploration and implementation '
                    'to its declared native role agents through spawn_agent.', 'spawn hooks')
CLAUDE_DELEGATION = ('Act as its declared initiator in this main session and coordinate delivery. Delegate repository exploration '
                     'and implementation to its declared role agents through the Agent tool (subagent_type = role name).', 'Agent hooks')
OWN_OUTPUT = ('SubagentStart', 'UserPromptSubmit', 'PermissionRequest')


def observed_transcript_model(raw):
    """Last assistant model recorded in a bounded subagent transcript."""
    if not isinstance(raw, str) or not raw:
        return None
    path = Path(raw).expanduser()
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > TRANSCRIPT_LIMIT:
            return None
        with path.open('rb') as handle:
            handle.seek(max(0, path.stat().st_size - TRANSCRIPT_TAIL))
            lines = handle.read().decode('utf-8', 'replace').splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            message = json.loads(line).get('message') or {}
        except ValueError:
            continue
        if isinstance(message, dict) and isinstance(message.get('model'), str):
            return message['model']
    return None


def review_context():
    return ('For this successfully completed top-level task only, include its cleansed .agentic/jev/event-*.json Q/A and native application evidence in the REVIEW_PIPELINE packet. '
            'Assess workflow fit, requested/observed models, permissions, fallback and missing measurements. Provide concrete followups with source, target, owner, done_when. '
            'Do not start review after failed/deferred delivery or inside loops; run the specialist pair once, never recursively. Do not call JEV to review JEV.')


def review_additional_context(packet):
    return review_context() + ' Explicitly read ' + packet + ' and its referenced decision records. These files are Git-ignored; do not rely on ordinary search to discover them.'


def workflow_context(workflow, delegation):
    sentence, hooks = delegation
    return ('JEV selected installed workflow ' + workflow['id'] + '. Load ' + workflow['path'] + ' and execute it for the ORIGINAL user request. '
            + sentence + ' Keep the scope of the ORIGINAL request; do not add requirements. Model routing happens automatically through '
            + hooks + '; omit guessed model overrides. ' + review_context())


def model_reason(result):
    return ('Role default ' if result.get('model_source') == 'role_default' else 'JEV selected ') + result['model']


def shared_output(core, project, name, event, result, delegation):
    """Hook output common to Codex and Claude, or None when the adapter decides."""
    if name == 'SubagentStart' and event.get('agent') == 'instruction-reviewer' and result.get('status') == 'observed':
        packet = core.review_packet(project, event['session_id'])
        return {'hookSpecificOutput': {'hookEventName': name, 'additionalContext': review_additional_context(packet)}} if packet else None
    if name == 'UserPromptSubmit' and result.get('status') == 'switched':
        # Blocking erases the switch prompt, so `/jev off|on|status` costs no model turn.
        return {'decision': 'block', 'reason': result['message']}
    if name == 'UserPromptSubmit' and result.get('workflow'):
        return {'hookSpecificOutput': {'hookEventName': name, 'additionalContext': workflow_context(result['workflow'], delegation)}}
    if name == 'PermissionRequest' and result.get('decision') in ('allow', 'deny'):
        return {'hookSpecificOutput': {'hookEventName': name, 'decision': {'behavior': result['decision'], 'message': 'Agentic JEV bounded permission decision'}}}
    return None


def safe_role(role):
    return bool(role) and '/' not in role and '\\' not in role


def codex_spawn(project, event, data):
    role = routing.canonical_role(data.get('agent_type') or data.get('task_name', ''))
    pin = None
    profile = project / '.codex/agents' / (role + '.toml')
    if safe_role(role) and profile.is_file():
        profile_text = profile.read_text(encoding='utf-8')
        match = routing.TOML_MODEL.search(profile_text)
        pin = match[1] if match else None
        description = re.search(r'^description\s*=\s*"([^"]+)"', profile_text, re.M)
        event['role_description'] = description[1] if description else None
    assignment = data.get('message') or data.get('prompt')
    if isinstance(assignment, str) and assignment.startswith(CODEX_ENCRYPTED_PREFIX):
        assignment = '[Host encrypted assignment; use original user scope and role, exact assignment unavailable]'
        event['assignment_unavailable'] = True
        event['input'] = {**data, 'message': assignment}
    event.update(kind='spawn', prompt=assignment, agent=role, pinned_model=data.get('model') or pin, continuation=bool(data.get('resume')))


def codex_event(core, project, payload):
    name = payload.get('hook_event_name')
    data = payload.get('tool_input') or {}
    event = {'host': 'codex', 'session_id': payload.get('session_id'),
             'event_id': payload.get('tool_use_id') or payload.get('agent_id') or payload.get('turn_id'), 'input': data, 'action': payload.get('tool_name')}
    if name == 'UserPromptSubmit':
        event.update(kind='prompt', prompt=payload.get('prompt', ''))
    elif name == 'PreToolUse' and payload.get('tool_name') in CODEX_SPAWN_TOOLS:
        codex_spawn(project, event, data)
    elif name == 'PermissionRequest':
        event.update(kind='permission', agent=routing.canonical_role(payload.get('agent_type')) or None)
    elif name == 'SubagentStart':
        event.update(kind='observation', agent=routing.canonical_role(payload.get('agent_type')), child_session_id=payload.get('agent_id'), observed_model=payload.get('model'))
    elif name == 'PostToolUse':
        event.update(kind='tool', resources=re.findall(WORKFLOW_RESOURCES, json.dumps(data)))
    else:
        return {}
    result = core.run_event(project, event)
    shared = shared_output(core, project, name, event, result, CODEX_DELEGATION)
    if shared is not None or name in OWN_OUTPUT:
        return shared or {}
    if name == 'PreToolUse' and result.get('model'):
        updated = {**data, 'model': result['model']}
        return {'hookSpecificOutput': {'hookEventName': name, 'permissionDecision': 'allow', 'updatedInput': updated, 'additionalContext': model_reason(result) + '; native role permissions and sandbox still apply.'}}
    return {}


def claude_spawn(project, event, data):
    role = routing.canonical_role(data.get('subagent_type', ''))
    pin = None
    profile = project / '.claude/agents' / (role + '.md')
    if safe_role(role) and profile.is_file():
        front = questions.parse_front(profile.read_text(encoding='utf-8')[:questions.FRONT_LIMIT])
        pin = front.get('model') if front.get('model') not in (None, '', 'inherit') else None
        event['role_description'] = front.get('description')
    event.update(kind='spawn', prompt=data.get('prompt') or data.get('description'), agent=role,
                 pinned_model=data.get('model') or pin, continuation=bool(data.get('resume')))


def claude_observation(event, payload, name):
    # SubagentStart carries no model on Claude Code; the actual model is read from the transcript at SubagentStop.
    observed = payload.get('model') or (observed_transcript_model(payload.get('agent_transcript_path')) if name == 'SubagentStop' else None)
    event.update(kind='observation', agent=routing.canonical_role(payload.get('agent_type')),
                 child_session_id=payload.get('agent_id'), phase=name, observed_model=observed)


def claude_event(core, project, payload):
    """Claude Code hooks: same decisions; the Agent tool accepts only opus/sonnet/haiku aliases."""
    name = payload.get('hook_event_name')
    data = payload.get('tool_input') if isinstance(payload.get('tool_input'), dict) else {}
    harness = name == 'UserPromptSubmit' and CLAUDE_HARNESS_PROMPT.match(str(payload.get('prompt', '')))
    if harness or (name == 'PermissionRequest' and payload.get('tool_name') in CLAUDE_DIALOG_TOOLS):
        return {}
    event = {'host': 'claude', 'session_id': payload.get('session_id'),
             'event_id': payload.get('tool_use_id') or payload.get('agent_id') or payload.get('prompt_id'),
             'input': data, 'action': payload.get('tool_name')}
    if name == 'UserPromptSubmit':
        event.update(kind='prompt', prompt=payload.get('prompt', ''))
    elif name == 'PreToolUse' and payload.get('tool_name') in CLAUDE_AGENT_TOOLS:
        claude_spawn(project, event, data)
    elif name == 'PermissionRequest':
        event.update(kind='permission', agent=routing.canonical_role(payload.get('agent_type')) or None)
    elif name in ('SubagentStart', 'SubagentStop'):
        claude_observation(event, payload, name)
    elif name == 'PostToolUse':
        event.update(kind='tool', resources=re.findall(WORKFLOW_RESOURCES, json.dumps(data)))
    else:
        return {}
    result = core.run_event(project, event)
    shared = shared_output(core, project, name, event, result, CLAUDE_DELEGATION)
    if shared is not None:
        return shared
    if name == 'PreToolUse' and result.get('model') in routing.CLAUDE_ALIASES:
        updated = {**data, 'model': result['model']}
        return {'hookSpecificOutput': {'hookEventName': name, 'permissionDecision': 'allow', 'updatedInput': updated, 'permissionDecisionReason': model_reason(result) + '; native role tools still apply.'}}
    return {}
