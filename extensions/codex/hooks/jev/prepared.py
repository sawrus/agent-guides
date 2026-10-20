"""Explicit, task-bound Codex model preparation. Never inspects encrypted assignments."""
import hashlib
import json
import os
import re
import time
import uuid

try:
    import tomllib
except ImportError:  # Python 3.10: accept only an unambiguous scalar subset.
    tomllib = None

VERSION = 2
TTL_SECONDS = 600
INPUT_LIMIT = 16384
# Codex agent names accept only lowercase letters, digits and underscores.
NAME = re.compile(r'^jev_([0-9a-f]{32})$')
ROLE = re.compile(r'^[a-z][a-z0-9_-]{0,95}$')


def failure(reason):
    return {'status': 'fallback', 'reason_code': reason, 'observed_model': None}


def enabled(core, project):
    return core.jev_settings(project).get('enabled') is True and os.environ.get('AGENTIC_ENABLE_JEV', '').lower() not in core.OFF


def read_record(core, path):
    if path.is_symlink():
        raise ValueError('redirected prepared metadata')
    value = core.read_json(path, {})
    return value if isinstance(value, dict) else {}


def binding(core, project, payload):
    session, task = payload.get('session_id'), payload.get('task_id')
    if not isinstance(session, str) or not session or not isinstance(task, str) or not task:
        return None
    context = read_record(core, core.private_dir(project) / ('context-' + core.short_hash(session) + '.json'))
    if context.get('task_id') != task or context.get('jev') != 'on':
        return None
    return {'project': str(project.resolve()), 'session_id': session, 'task_id': task,
            'generation': context.get('generation', context.get('task_generation'))}


def profile_data(project, role):
    if not ROLE.fullmatch(role):
        raise ValueError('invalid agent role')
    path = project / '.codex' / 'agents' / (role + '.toml')
    if path.is_symlink() or path.parent.is_symlink() or path.parent.parent.is_symlink():
        raise ValueError('redirected agent profile')
    if not path.is_file():
        return {}
    if path.stat().st_size > INPUT_LIMIT:
        raise ValueError('agent profile too large')
    text = path.read_text(encoding='utf-8')
    if tomllib is not None:
        return tomllib.loads(text)
    # A regex search could mistake an instruction example for a native model pin.
    # Without a TOML parser, complex profiles stay with native routing.
    if '"""' in text or "'" * 3 in text:
        raise ValueError('multiline profile needs TOML parser')
    result = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        match = re.fullmatch(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\"(?:[^\"\\]|\\.)*\"|'[^']*')\s*(?:#.*)?", line)
        if not match or match[1] in result:
            raise ValueError('ambiguous profile needs TOML parser')
        raw = match[2]
        result[match[1]] = json.loads(raw) if raw.startswith('"') else raw[1:-1]
    return result


def profile_pin(core, project, role):
    model = profile_data(project, role).get('model')
    if model is not None and (not isinstance(model, str) or not model):
        raise ValueError('invalid native model pin')
    return model


def preserve_profile(project, role):
    """Keep every native instruction or execution setting on its canonical profile."""
    ordinary = {'name', 'description', 'model'}
    return bool(set(profile_data(project, role)) - ordinary)


def current_public(core, project, payload, record):
    if not enabled(core, project):
        return failure('disabled')
    rejected = checked(core, project, payload, record)
    if rejected:
        return rejected
    if record.get('status') == 'prepared':
        try:
            if profile_pin(core, project, record['role']) != record.get('profile_pin'):
                return failure('profile_pin_changed')
            if preserve_profile(project, record['role']) != record.get('preserve_profile'):
                return failure('profile_policy_changed')
        except (OSError, ValueError, TypeError, KeyError):
            return failure('prepared_profile_unavailable')
    return public(record)


def models(core, project):
    unavailable = core.read_json(core.private_dir(project) / 'availability.json', {})
    return {model['id'] for model in core.codex_models(project)
            if unavailable.get('codex:' + model['id'], 0) <= time.time()}


def spawn_model(record):
    """A native profile pin cannot be changed by spawn arguments; the host applies it without a model override."""
    return None if record.get('model_source') == 'user_pin' else record.get('recommended_model')


def accepted(result):
    return result.get('status') == 'prepared' and result.get('application_status') in ('submitted_unconfirmed', 'observed')


def public(record):
    """`spawn` is the only callable location: `agent_type` selects the canonical profile, `task_name` the registry record."""
    fields = ('status', 'reason_code', 'decision_id', 'role', 'recommended_model',
              'submitted_model', 'observed_model', 'model_source', 'expires_at', 'application_status', 'correlation_status')
    result = {key: record.get(key) for key in fields}
    if record.get('status') == 'prepared' and record.get('recommended_model') and not record.get('tool_use_id'):
        spawn = {'agent_type': record['role'], 'task_name': record['task_name'], 'model': spawn_model(record), 'fork_turns': 'none'}
        result['spawn'] = {key: value for key, value in spawn.items() if value is not None}
        result['on_reject'] = 'native_default_report'
    return result


def prepare(core, project, payload):
    """Reserve an idempotency key before evaluating: a crash never triggers a second paid call."""
    if not enabled(core, project):
        return failure('disabled')
    bound = binding(core, project, payload)
    if not bound:
        return failure('prepared_task_mismatch')
    required = ('request_id', 'role', 'goal', 'scope', 'complexity')
    # Coordinators sometimes send a file list for scope; a list of strings is the same open text.
    payload = {**payload, **{key: '; '.join(payload[key]) for key in ('goal', 'scope', 'complexity')
                             if isinstance(payload.get(key), list) and all(isinstance(item, str) for item in payload[key])}}
    if any(payload.get(key) is not None and not isinstance(payload[key], str) for key in required):
        return failure('prepared_metadata_invalid')
    if any(not isinstance(payload.get(key), str) or not payload[key].strip() for key in required):
        return failure('prepared_metadata_missing')
    if not ROLE.fullmatch(payload['role']) or len(payload['request_id']) > 256:
        return failure('prepared_metadata_invalid')
    if len(json.dumps({key: payload[key] for key in required}, ensure_ascii=False).encode()) > INPUT_LIMIT:
        return failure('prepared_input_too_large')
    # Hash and persist only scrubbed task details. No raw assignment is stored.
    clean = core.scrub({key: payload[key] for key in required}, project)
    role = core.routing.canonical_role(clean['role'])
    profile = project / '.codex' / 'agents' / (role + '.toml')
    if not ROLE.fullmatch(role) or not profile.is_file() or profile.is_symlink() or profile.parent.is_symlink() or profile.parent.parent.is_symlink():
        return failure('prepared_role_unavailable')
    fingerprint = hashlib.sha256(json.dumps(clean, sort_keys=True).encode()).hexdigest()
    identity = json.dumps({**bound, 'request_id': clean['request_id']}, sort_keys=True)
    request_path = core.private_dir(project) / ('prepare-request-' + hashlib.sha256(identity.encode()).hexdigest() + '.json')
    with core.file_lock(request_path):
        existing = read_record(core, request_path)
        if existing:
            if existing.get('fingerprint') != fingerprint:
                return failure('prepared_request_conflict')
            if not re.fullmatch(r'[0-9a-f]{32}', str(existing.get('decision_id', ''))):
                return failure('prepared_metadata_invalid')
            record = read_record(core, core.private_dir(project) / ('prepared-' + existing['decision_id'] + '.json'))
            if record.get('expires_at', 0) <= time.time():
                return failure('prepared_expired')
            return current_public(core, project, payload, record)
        decision_id = uuid.uuid4().hex
        path = core.private_dir(project) / ('prepared-' + decision_id + '.json')
        record = {**bound, 'role': role, 'fingerprint': fingerprint, 'decision_id': decision_id,
                  'task_name': 'jev_' + decision_id, 'expires_at': time.time() + TTL_SECONDS,
                  'status': 'fallback', 'reason_code': 'prepared_incomplete', 'model_source': 'none',
                  'recommended_model': None, 'submitted_model': None, 'observed_model': None,
                  'application_status': 'unconfirmed'}
        core.save_json(path, record)
        core.save_json(request_path, {'decision_id': decision_id, 'fingerprint': fingerprint})
        try:
            pin = profile_pin(core, project, role)
            record['profile_pin'] = pin
            record['preserve_profile'] = preserve_profile(project, role)
            record['correlation_status'] = 'awaiting_native_binding'
            if pin:
                result = {'status': 'preserved', 'model': pin, 'model_source': 'user_pin'}
            else:
                budget = max(1, (core.questions.ASSIGNMENT_LIMIT - 96) // 3)
                parts = []
                for key in ('goal', 'scope', 'complexity'):
                    text, truncated = core.questions.clip(clean[key], budget)
                    parts.append(key + ': ' + text + (' [truncated]' if truncated else ''))
                assignment = '\n'.join(parts)
                result = core.run_event(project, {'host': 'codex', 'kind': 'spawn', 'session_id': bound['session_id'],
                    'event_id': 'prepare-' + decision_id, 'agent': role, 'prompt': assignment,
                    'assignment_unavailable': False, 'preparation_only': True})
            model = result.get('model')
            eligible_result = result.get('status') in ('evaluated', 'routed', 'preserved') or result.get('model_source') == 'role_default'
            if model and model in models(core, project) and eligible_result:
                record.update(status='prepared', reason_code=result.get('reason_code'), recommended_model=model,
                              model_source=result.get('model_source', 'jev_tier'))
            else:
                record.update(reason_code=result.get('reason_code') or 'prepared_model_unavailable')
        except (OSError, ValueError, TypeError, KeyError):
            record.update(reason_code='prepared_request_failed')
        core.save_json(path, record)
        return current_public(core, project, payload, record)


def record_path(core, project, payload):
    match = NAME.fullmatch(str(payload.get('task_name', '')))
    return core.private_dir(project) / ('prepared-' + match[1] + '.json') if match else None


def checked(core, project, payload, record):
    bound = binding(core, project, payload)
    if not bound or any(record.get(key) != value for key, value in bound.items()):
        return failure('prepared_task_mismatch')
    if record.get('expires_at', 0) <= time.time():
        return failure('prepared_expired')
    return None


def resolve_role(core, project, task_name):
    """Profile lookup only, never a substitute for claim's binding and single-use checks."""
    path = record_path(core, project, {'task_name': task_name})
    record = read_record(core, path) if path else {}
    return record.get('role') if record.get('expires_at', 0) > time.time() else None


def claim(core, project, payload):
    if not enabled(core, project):
        return failure('disabled')
    path = record_path(core, project, payload)
    if not path or not isinstance(payload.get('tool_use_id'), str) or not payload['tool_use_id']:
        return failure('prepared_metadata_missing')
    with core.file_lock(path):
        record = read_record(core, path)
        if not record:
            return failure('prepared_metadata_missing')
        rejected = checked(core, project, payload, record)
        if rejected:
            return rejected
        if record.get('tool_use_id') and record['tool_use_id'] != payload['tool_use_id']:
            return failure('prepared_already_claimed')
        if payload.get('agent_type') != record.get('role'):
            return failure('prepared_agent_type_mismatch')
        if record.get('status') != 'prepared':
            return public(record)
        if record.get('tool_use_id') and record.get('submitted_model') != payload.get('model'):
            return failure('prepared_submission_conflict')
        record.update(tool_use_id=payload['tool_use_id'], submitted_model=payload.get('model'))
        try:
            pin = profile_pin(core, project, record['role'])
            if preserve_profile(project, record['role']) != record.get('preserve_profile'):
                record.update(status='fallback', reason_code='profile_policy_changed')
            elif pin != record.get('profile_pin'):
                record.update(status='fallback', reason_code='profile_pin_changed')
            elif payload.get('fork_turns') != 'none':
                record.update(status='fallback', reason_code='prepared_fork_incompatible')
            elif payload.get('model') != spawn_model(record):
                record.update(status='fallback', reason_code='submitted_model_override', model_source='user_pin')
            elif record['recommended_model'] not in models(core, project):
                record.update(status='fallback', reason_code='prepared_model_unavailable')
            else:
                record.update(application_status='observed' if record.get('observed_model') else 'submitted_unconfirmed',
                              correlation_status='native_child_bound' if record.get('observed_model') else 'submission_bound')
        except (OSError, ValueError):
            record.update(status='fallback', reason_code='prepared_profile_unavailable')
        core.save_json(path, record)
        return public(record)


def observe(core, project, payload):
    """Caller must supply only the actual native model; submitted or recommended values are not evidence."""
    if not enabled(core, project):
        return failure('disabled')
    path = record_path(core, project, payload)
    if not path:
        return failure('prepared_metadata_missing')
    with core.file_lock(path):
        record = read_record(core, path)
        rejected = checked(core, project, payload, record)
        if rejected:
            return rejected
        if not record.get('tool_use_id') or record['tool_use_id'] != payload.get('tool_use_id'):
            return failure('prepared_observation_unbound')
        model = payload.get('observed_model')
        if not isinstance(model, str) or not model:
            return failure('prepared_observation_missing')
        record.update(observed_model=model, application_status='observed', correlation_status='native_child_bound')
        core.save_json(path, record)
        return public(record)


def link_child(core, project, payload):
    """Bind only a successful native tool_response.task_name, extracted by the adapter."""
    if not enabled(core, project):
        return failure('disabled')
    path = record_path(core, project, payload)
    if not path:
        return failure('prepared_metadata_missing')
    child = payload.get('child_session_id')
    if not isinstance(child, str) or len(child) > 1024 or not child.startswith('/') or not child.endswith('/' + payload['task_name']):
        return failure('prepared_child_unbound')
    with core.file_lock(path):
        record = read_record(core, path)
        rejected = checked(core, project, payload, record)
        if rejected:
            return rejected
        if not record.get('tool_use_id') or record['tool_use_id'] != payload.get('tool_use_id'):
            return failure('prepared_child_unbound')
        if record.get('child_task_name') and record['child_task_name'] != child:
            return failure('prepared_child_conflict')
        record['child_task_name'] = child
        pending = record.get('pending_observation')
        if pending and not record.get('observation_conflict'):
            if pending['child_session_id'] == child and pending['tool_use_id'] == record['tool_use_id']:
                record.update(observed_model=pending['observed_model'], application_status='observed', correlation_status='native_child_bound')
                record.pop('pending_observation', None)
            else:
                record.update(observation_conflict=True, application_status='unconfirmed', correlation_status='observation_conflict')
        core.save_json(path, record)
        return public(record)


def observe_child(core, project, payload):
    """Keep at most one bounded native observation until its exact successful spawn response arrives."""
    if not enabled(core, project):
        return failure('disabled')
    child = payload.get('child_session_id')
    if not isinstance(child, str) or not child.startswith('/') or len(child) > 1024:
        return failure('prepared_child_unbound')
    model = payload.get('observed_model')
    if not isinstance(model, str) or not model or len(model) > 256:
        return failure('prepared_observation_missing')
    task_name = child.rsplit('/', 1)[-1]
    path = record_path(core, project, {'task_name': task_name})
    if not path:
        return failure('prepared_child_unbound')
    with core.file_lock(path):
        record = read_record(core, path)
        rejected = checked(core, project, payload, record)
        if rejected:
            return rejected
        if not record.get('tool_use_id'):
            return failure('prepared_child_unbound')
        if record.get('observation_conflict'):
            return failure('prepared_observation_conflict')
        observation = {'child_session_id': child, 'observed_model': model, 'tool_use_id': record['tool_use_id']}
        pending = record.get('pending_observation')
        if pending and pending != observation:
            record.update(observation_conflict=True, application_status='unconfirmed', correlation_status='observation_conflict')
            core.save_json(path, record)
            return failure('prepared_observation_conflict')
        linked = record.get('child_task_name')
        if linked is None:
            record['pending_observation'] = observation
            core.save_json(path, record)
            return failure('prepared_child_unbound')
        if linked != child:
            return failure('prepared_child_unbound')
        if record.get('observed_model') and record['observed_model'] != model:
            record.update(observation_conflict=True, observed_model=None, application_status='unconfirmed', correlation_status='observation_conflict')
            core.save_json(path, record)
            return failure('prepared_observation_conflict')
        record.update(observed_model=model, application_status='observed', correlation_status='native_child_bound')
        core.save_json(path, record)
        return public(record)
