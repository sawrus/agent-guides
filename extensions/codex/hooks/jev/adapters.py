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
SESSION_META_LIMIT = 1048576
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
# `lean` installs no role agents: the workflow is a checklist for the native main session, which keeps its own
# planning and delegation. Spawn hooks still route the models of the subagents it chooses to start.
LEAN_CONTEXT = ('JEV suggests installed workflow {id}. Use {path} as a checklist for the ORIGINAL user request and perform '
                'its steps yourself in this main session; there are no role agents. Start a subagent only where the project '
                'core rules call for one; {hooks} route its model, so omit guessed model overrides. Keep the scope of the '
                'ORIGINAL request; do not add requirements.')


def install_profile(project):
    """Installed profile from .agentic.json; manifests without one predate `lean`, when JEV always installed `team`."""
    try:
        settings = json.loads((project / '.agentic.json').read_text(encoding='utf-8')).get('settings') or {}
    except (OSError, ValueError, AttributeError):
        return 'team'
    profile = settings.get('profile') if isinstance(settings, dict) else None
    return profile if profile in ('lean', 'team') else 'team'


def prepared_name(task_name):
    return bool(re.fullmatch(r'jev_[0-9a-f]{32}', task_name))


def codex_child_path(payload):
    """Canonical child path for SubagentStart, whose agent_id is a thread id. The host-supplied transcript must
    name that same thread; otherwise the observation stays unbound."""
    agent_id, raw = payload.get('agent_id'), payload.get('transcript_path')
    if isinstance(agent_id, str) and agent_id.startswith('/'):
        return agent_id
    if not isinstance(agent_id, str) or not agent_id or not isinstance(raw, str) or not raw:
        return None
    path = Path(raw).expanduser()
    try:
        if path.is_symlink() or not path.is_file():
            return None
        with path.open('rb') as handle:
            meta = json.loads(handle.readline(SESSION_META_LIMIT)).get('payload') or {}
        if meta.get('id') == agent_id and isinstance(meta.get('agent_path'), str):
            return meta['agent_path']
    except (OSError, ValueError, AttributeError):
        pass
    return None


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


def workflow_context(workflow, delegation, lean=False):
    sentence, hooks = delegation
    if lean:
        return LEAN_CONTEXT.format(id=workflow['id'], path=workflow['path'], hooks=hooks)
    return ('JEV selected installed workflow ' + workflow['id'] + '. Load ' + workflow['path'] + ' and execute it for the ORIGINAL user request. '
            + sentence + ' Keep the scope of the ORIGINAL request; do not add requirements. Model routing happens automatically through '
            + hooks + '; omit guessed model overrides (Codex prepared selections are explicit exceptions). ' + review_context())


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
        lean = install_profile(project) == 'lean'
        context = workflow_context(result['workflow'], delegation, lean)
        # Prepared spawns serve role delegation; lean spawns are routed by the PreToolUse spawn hook alone.
        if event.get('host') == 'codex' and not lean:
            task = core.read_json(core.private_dir(project) / ('context-' + core.short_hash(event['session_id']) + '.json'), {})
            context += (' Before each Codex V2 spawn, call the local JSON interface: python3 .agent/jev/hook.py --host codex --prepare-spawn. '
                        'Send session_id=' + str(event['session_id']) + ', task_id=' + str(task.get('task_id')) +
                        ', a unique request_id, canonical role, goal, scope and complexity via JSON stdin (all values are plain strings). '
                        'Copy every field of the returned spawn object (agent_type, task_name, model when present, fork_turns) unchanged and add only the complete message; '
                        'no other response field is a spawn argument. agent_type keeps the canonical role profile and its restrictions. '
                        'A prepared model is an authorized routing selection, not a guessed override. User pins win. '
                        'If the interface returns no spawn, retain native role defaults. If the hook denies a prepared launch, spawn once with native role defaults '
                        '(agent_type only, no model), do not retry the ticket or prepare again for that launch, and report recommendation_discarded with the reason code. '
                        'Do not invent spawn arguments or decrypt assignments.')
        return {'hookSpecificOutput': {'hookEventName': name, 'additionalContext': context}}
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
             'event_id': payload.get('tool_use_id') or payload.get('agent_id') or payload.get('turn_id'), 'input': data, 'action': payload.get('tool_name'), 'cwd': payload.get('cwd')}
    if name == 'UserPromptSubmit':
        event.update(kind='prompt', prompt=payload.get('prompt', ''))
    elif name == 'PreToolUse' and payload.get('tool_name') in CODEX_SPAWN_TOOLS:
        if isinstance(data.get('task_name'), str) and prepared_name(data['task_name']):
            return prepared_submission(core, project, payload, event)
        codex_spawn(project, event, data)
    elif name == 'PermissionRequest':
        event.update(kind='permission', agent=routing.canonical_role(payload.get('agent_type')) or None)
    elif name == 'SubagentStart':
        event.update(kind='observation', agent=routing.canonical_role(payload.get('agent_type')),
                     child_session_id=codex_child_path(payload) or payload.get('agent_id'), observed_model=payload.get('model'))
    elif name == 'PostToolUse':
        event.update(kind='tool', resources=re.findall(WORKFLOW_RESOURCES, json.dumps(data)))
    else:
        return {}
    result = core.run_event(project, event)
    if name == 'PostToolUse' and payload.get('tool_name') in CODEX_SPAWN_TOOLS:
        prepared_post(core, project, payload)
    if name == 'SubagentStart':
        prepared_observation(core, project, payload, event['child_session_id'])
    shared = shared_output(core, project, name, event, result, CODEX_DELEGATION)
    if shared is not None or name in OWN_OUTPUT:
        return shared or {}
    if name == 'PreToolUse' and result.get('model'):
        updated = {**data, 'model': result['model']}
        return {'hookSpecificOutput': {'hookEventName': name, 'permissionDecision': 'allow', 'updatedInput': updated, 'additionalContext': model_reason(result) + '; native role permissions and sandbox still apply.'}}
    return {}


def prepared_context(core, project, session):
    return core.read_json(core.private_dir(project) / ('context-' + core.short_hash(session) + '.json'), {})


def reject_prepared(reason):
    return {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
        'permissionDecisionReason': 'Prepared launch is invalid (' + str(reason) + '); recommendation_discarded. Spawn once with the canonical native role '
        'defaults/pins (agent_type only, no model), do not retry the ticket or prepare again for this launch, and report this reason code.'}}


def prepared_submission(core, project, payload, event):
    """Never auto-approve. Invalid tickets cannot execute with a stale model/profile."""
    if not core.plain_enabled(project):
        return reject_prepared('disabled')
    try:
        import prepared
        data = payload.get('tool_input') or {}
        context = prepared_context(core, project, event.get('session_id'))
        result = prepared.claim(core, project, {**data, 'session_id': event.get('session_id'),
            'task_id': context.get('task_id'), 'tool_use_id': payload.get('tool_use_id')})
        role = prepared.resolve_role(core, project, data.get('task_name'))
        event.update(kind='spawn', agent=role, prepared_decision=result,
                     input={key: data[key] for key in ('agent_type', 'task_name', 'model', 'fork_turns') if key in data})
        core.run_event(project, event)
        if not prepared.accepted(result):
            return reject_prepared(result.get('reason_code') or 'unconfirmed')
    except (ImportError, OSError, ValueError, TypeError, KeyError):
        return reject_prepared('metadata_unavailable')
    return {}


def prepared_post(core, project, payload):
    if not core.plain_enabled(project):
        return {}
    try:
        import prepared
        data = payload.get('tool_input') or {}
        response = payload.get('tool_response')
        # Codex 0.163.0 returns the spawn result as a JSON string: '{"task_name":"/root/<name>"}'.
        if isinstance(response, str) and len(response) <= SESSION_META_LIMIT:
            response = json.loads(response)
        if not isinstance(response, dict):
            return
        context = prepared_context(core, project, payload.get('session_id'))
        prepared.link_child(core, project, {**data, 'session_id': payload.get('session_id'),
            'task_id': context.get('task_id'), 'tool_use_id': payload.get('tool_use_id'),
            'child_session_id': response.get('task_name')})
    except (ImportError, AttributeError, OSError, ValueError, TypeError, KeyError):
        pass


def prepared_observation(core, project, payload, child):
    if not core.plain_enabled(project):
        return {}
    try:
        import prepared
        context = prepared_context(core, project, payload.get('session_id'))
        prepared.observe_child(core, project, {'session_id': payload.get('session_id'),
            'task_id': context.get('task_id'), 'child_session_id': child,
            'observed_model': payload.get('model')})
    except (ImportError, AttributeError, OSError, ValueError, TypeError, KeyError):
        pass


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
             'input': data, 'action': payload.get('tool_name'), 'cwd': payload.get('cwd')}
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
