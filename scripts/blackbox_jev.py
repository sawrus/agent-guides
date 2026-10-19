#!/usr/bin/env python3
"""Opt-in paid, real-CLI JEV integration checks. Never replace native trust or permissions."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import tempfile
import threading
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'extensions/codex/hooks/jev'))
sys.path.insert(0, str(ROOT / 'tests/notify'))
from api import key_for, redact  # noqa: E402
from fake_telegram import FakeTelegram  # noqa: E402

PROMPT = 'разработай калькулятор'
# One bounded reply when the coordinator stops to ask for approval (for example new root files).
FOLLOWUP = ('Подтверждаю: создавай нужные файлы, включая файлы в корне, и используй предложенный минимальный scope. '
            'Доведи работу до конца без дополнительных вопросов.')
HOSTS = ('codex', 'opencode', 'claude')
# Every host delivers through the shared .agent/notify runtime (OpenCode via its plugin).
TELEGRAM_HOSTS = HOSTS
CLAUDE_ROLES = ('product-owner', 'team-lead', 'developer', 'qa', 'devops-engineer', 'analyst', 'pm',
                'instruction-reviewer', 'memory-curator')
# Session variables of an enclosing Claude Code run; the nested CLI must start its own session.
CLAUDE_SESSION_ENV = ('CLAUDECODE', 'CLAUDE_CODE_ENTRYPOINT', 'CLAUDE_CODE_SSE_PORT', 'CLAUDE_PROJECT_DIR',
                      'CLAUDE_ENV_FILE', 'CLAUDE_CODE_SESSION_ID', 'CLAUDE_CODE_SESSION_ACCESS_TOKEN')
CLAUDE_ALLOWED_TOOLS = ('Bash(python3:*) Bash(python:*) Bash(node:*) Bash(npm:*) Bash(npx:*) Bash(pytest:*) Bash(ruff:*) '
                        'Bash(make:*) Bash(git:*) Bash(ls:*) Bash(mkdir:*) Bash(cat:*)')


def clean(text):
    keys = [key_for(ROOT, name) for name in ('JEV_API_KEY', 'TYPESAFE_API_KEY')]
    def cleanse(value):
        value = redact(value)
        if isinstance(value, dict):
            return {k: cleanse(v) for k, v in value.items()}
        if isinstance(value, list):
            return [cleanse(v) for v in value]
        if isinstance(value, str):
            for key in keys:
                if key:
                    value = value.replace(key, '[REDACTED]')
        return value
    try:
        value = json.loads(text)
    except ValueError:
        return cleanse(text)
    return json.dumps(cleanse(value), ensure_ascii=False) + ('\n' if text.endswith('\n') else '')


def prepare(host, root, endpoint):
    (root / host).mkdir(parents=True, exist_ok=True)
    project = Path(tempfile.mkdtemp(prefix=f'agentic-jev-blackbox-{host}-'))
    (root / host / 'project.json').write_text(json.dumps({'path': str(project)}))
    subprocess.run(['git', 'init', '-q', str(project)], check=True)
    subprocess.run(['git', '-C', str(project), '-c', 'user.name=Agentic Blackbox', '-c', 'user.email=blackbox@localhost', 'commit', '--allow-empty', '-q', '-m', 'Initialize isolated blackbox project'], check=True)
    install_project(host, project, root, endpoint)
    return project


def install_project(host, project, root, endpoint):
    extra = ['--enable-telegram'] if host in TELEGRAM_HOSTS else []
    result = subprocess.run([str(ROOT / 'target/debug/agentic'), 'install', '--project-dir', str(project),
                             '--agent-os', host, '--areas', 'software', '--specializations',
                             'software.backend,software.general', '--enable-jev', '--jev-api-url', endpoint,
                             '--no-doctor', *extra], capture_output=True, text=True)
    (root / host / 'install.log').write_text(clean(result.stdout + result.stderr))
    if result.returncode:
        raise RuntimeError('Agentic install failed; inspect install.log')
    if host in TELEGRAM_HOSTS:
        prepare_telegram_credentials(host, root)
    if host == 'claude':
        prepare_claude_evidence(project, root)


def prepare_telegram_credentials(host, root):
    """Run-local fake credentials; the real ~/.config/agentic is never read or written."""
    config = root / host / 'agentic-config'
    config.mkdir(parents=True, exist_ok=True)
    (config / 'config.json').write_text(json.dumps({'notifications': {'telegram': {'botToken': 'blackbox-token', 'chatId': '1'}}}))


def telegram_fired(trace):
    path = trace.parent / 'telegram.json'
    telegram = json.loads(path.read_text()) if path.exists() else {}
    return any('Задача завершена' in text for text in telegram.get('messages', []))


def prepare_claude_evidence(project, root):
    """Run-local evidence only: an instructions-load log."""
    log = root / 'claude' / 'instructions.jsonl'
    recorder = ('import json,sys; e=json.load(sys.stdin); '
                f'open({json.dumps(str(log))},"a").write(json.dumps({{"file_path":e.get("file_path"),"memory_type":e.get("memory_type"),"load_reason":e.get("load_reason")}})+"\\n")')
    local = {'hooks': {'InstructionsLoaded': [{'matcher': '', 'hooks': [{'type': 'command', 'command': f'{sys.executable} -c {json.dumps(recorder)}', 'timeout': 5}]}]}}
    (project / '.claude' / 'settings.local.json').write_text(json.dumps(local, indent=2))


def native_success(trace):
    """Claude stream-json ends each turn with a result event; every turn must succeed."""
    results = []
    for line in trace.read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('type') == 'result':
            results.append(event.get('subtype') == 'success' and not event.get('is_error'))
    return bool(results) and all(results)


def claude_init(trace):
    for line in trace.read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            return event
    return {}


def names(items):
    return {item if isinstance(item, str) else (item or {}).get('name', '') for item in items or []}


def claude_checks(project, trace):
    init = claude_init(trace)
    agents = names(init.get('agents'))
    commands = names(init.get('slash_commands'))
    skills = names(init.get('skills')) | commands
    installed_skills = {p.parent.name for p in (project / '.claude/skills').glob('*/SKILL.md')}
    instructions = trace.parent / 'instructions.jsonl'
    loaded = instructions.read_text() if instructions.exists() else ''
    return {'agents_loaded': set(CLAUDE_ROLES) <= agents,
            'commands_visible': 'develop-feature' in commands,
            'skills_visible': bool(installed_skills & skills),
            'rules_loaded': '.claude/rules/' in loaded,
            'telegram_fired': telegram_fired(trace)}


def codex_sandbox():
    sandbox = os.environ.get('BLACKBOX_CODEX_SANDBOX', 'workspace-write')
    if sandbox not in ('workspace-write', 'danger-full-access'):
        raise ValueError('BLACKBOX_CODEX_SANDBOX must be workspace-write or danger-full-access')
    return sandbox


def native_session(trace):
    """First session id the host reports: Codex thread, Claude init, or OpenCode event."""
    for line in trace.read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('type') == 'thread.started':
            return event.get('thread_id')
        if event.get('type') == 'system' and event.get('subtype') == 'init':
            return event.get('session_id')
        if event.get('sessionID'):
            return event['sessionID']
    return None


def followup_turn(host, executable, command, trace):
    """(command, stdin) that resumes the same native session with the single FOLLOWUP reply."""
    session = native_session(trace)
    if not session:
        return None
    if host == 'claude':
        return command[:2] + ['--resume', session] + command[2:], FOLLOWUP
    if host == 'opencode':
        return command + ['--session', session], FOLLOWUP
    # `codex exec resume` has no --sandbox/-C flags; cwd is already the project.
    return [executable, '--no-daemon', 'exec', 'resume', '--json', '--skip-git-repo-check',
            '-c', f'sandbox_mode="{codex_sandbox()}"', session, FOLLOWUP], None


def calculator_probe(project):
    """The agent selects the stack. Validate its delivered public entrypoint separately with explicit evidence."""
    probe_command = [sys.executable, str(ROOT / 'scripts/blackbox_calculator_probe.py'), str(project)]
    verifier = os.environ.get('BLACKBOX_VERIFIER')
    if verifier:
        probe_command = [str(Path(verifier).resolve()), str(project)]
    try:
        probe = subprocess.run(probe_command, cwd=project, capture_output=True, text=True, timeout=30)
        evidence = json.loads(probe.stdout)
        return probe.returncode == 0 and evidence.get('verified') is True, evidence
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False, {'verified': False, 'reason': 'Independent calculator probe failed'}


def agent_label(record):
    """Installed roles are labelled `agent`; native helpers such as Explore keep `native_agent_type` (QR-D6)."""
    return record['context'].get('agent') or record['context'].get('native_agent_type')


def verify(project, trace, exit_code, host=None):
    records = [json.loads(p.read_text()) for p in (project / '.agentic/jev').glob('event-*.json')]
    session = native_session(trace)
    prompts = [r for r in records if r['context']['kind'] == 'prompt' and r['context'].get('prompt') == PROMPT and r['context'].get('session_id') == session]
    tasks = {r['context'].get('task_id') for r in prompts}
    records = [r for r in records if r['context'].get('task_id') in tasks]
    workflow_records = [r for r in prompts if r['result'].get('workflow') and r['result']['status'] == 'evaluated']
    workflows = [r['result']['workflow'] for r in workflow_records]
    reads = [json.dumps(r['context'], ensure_ascii=False) for r in records if r['context']['kind'] == 'tool']
    workflow_applied = any(w['path'] in row for w in workflows for row in reads)
    routes = [r for r in records if r['context']['kind'] == 'spawn' and r['result'].get('model')]
    observed = [r for r in records if r['context']['kind'] == 'observation' and r['result'].get('observed_model')]
    # Match a child/role observation to the routed parent/role, rather than any mentioned model string.
    def same_model(requested, observed):
        # Claude routes by alias (haiku) while transcripts record full ids (claude-haiku-...).
        return requested == observed or (host == 'claude' and isinstance(observed, str) and f'-{requested}-' in f'-{observed}-')
    model_applied = any(a['result']['status'] == 'evaluated' and same_model(a['result']['model'], b['result']['observed_model'])
                        and a['context'].get('session_id') == b['context'].get('session_id')
                        and agent_label(a) == agent_label(b) for a in routes for b in observed)
    checks = {'native_exit_success': exit_code == 0, 'real_jev_workflow': bool(workflow_records),
              'workflow_read_by_agent': workflow_applied, 'model_applied_to_subagent': model_applied,
              'calculator_verified': False}
    if host == 'claude':
        checks.update(claude_checks(project, trace))
    elif host in TELEGRAM_HOSTS:
        checks['telegram_fired'] = telegram_fired(trace)
    checks['calculator_verified'], evidence = calculator_probe(project)
    (trace.parent / 'calculator-check.json').write_text(clean(json.dumps(evidence, ensure_ascii=False, indent=2)))
    cost = sum(r['result'].get('usage', {}).get('cost_usd') or 0 for r in records)
    return {'status': 'passed' if all(checks.values()) else 'failed', 'checks': checks,
            'workflow': [w['id'] for w in workflows], 'requested_models': [r['result']['model'] for r in routes],
            'observed_models': [r['result']['observed_model'] for r in observed],
            'jev_reported_cost_usd': cost, 'trace': str(trace), 'project': str(project),
            'calculator_evidence': str(trace.parent / 'calculator-check.json'),
            'limitation': 'Built-in arithmetic probe supports Python/JavaScript public evaluators; other stacks require BLACKBOX_VERIFIER. Self-reported tests do not pass.'}


def run(host, project, root, timeout):
    executable = shutil.which(host)
    if not executable:
        return {'status': 'blocked', 'reason': f'{host} is not installed'}
    env = os.environ.copy()
    env["PWD"] = str(project)
    # The nested CLI must create its own session/tool transport, not inherit this chat's payload.
    # Keep CODEX_HOME and all sandbox/permission policy variables intact.
    for name in ('CODEX_REMOTE_PAYLOAD', 'CODEX_THREAD_ID', 'CODEX_SESSION_ID'):
        env.pop(name, None)
    budget = ROOT / '.agentic-blackbox/jev-budget.json'
    if not budget.exists():
        budget.parent.mkdir(parents=True, exist_ok=True)
        budget.write_text(json.dumps({'limit_usd': 5, 'committed_usd': .02, 'calls': 0, 'pending': {}}))
    env['AGENTIC_JEV_BUDGET_FILE'] = str(budget)
    for key in ('JEV_API_KEY', 'TYPESAFE_API_KEY'):
        value = key_for(ROOT, key)
        if value:
            env[key] = value
    # Use existing auth. No HOME/CODEX_HOME replacement, --pure, or permission/trust bypass.
    telegram = None
    if host in TELEGRAM_HOSTS:
        telegram = FakeTelegram().__enter__()
        env['AGENTIC_TELEGRAM_API_BASE_URL'] = telegram.url
        env['AGENTIC_CONFIG_DIR'] = str(root / host / 'agentic-config')
    if host == 'codex':
        # Hosts that block unprivileged user namespaces (bwrap) need an explicit override, e.g. danger-full-access.
        command = [executable, '--no-daemon', 'exec', '--json', '--skip-git-repo-check', '--sandbox', codex_sandbox(), '-C', str(project), PROMPT]
    elif host == 'claude':
        for name in CLAUDE_SESSION_ENV:
            env.pop(name, None)
        model = os.environ.get('BLACKBOX_CLAUDE_MODEL', 'sonnet')
        # Edits stay inside the project; only the listed test commands run without a prompt.
        command = [executable, '-p', '--output-format', 'stream-json', '--verbose', '--permission-mode', 'acceptEdits',
                   '--model', model, '--allowedTools', CLAUDE_ALLOWED_TOOLS]  # variadic flag: prompt goes to stdin
    else:
        env['AGENTIC_JEV_MODEL_PROVIDER'] = 'openai'
        primary = os.environ.get('BLACKBOX_OPENCODE_MODEL', 'openai/gpt-6-luna')
        if not primary.startswith('openai/'):
            raise ValueError('OpenCode blackbox is restricted to OpenAI models')
        command = [executable, 'run', '--standalone', '--model', primary, '--format', 'json']
    trace = root / host / 'trace.jsonl'
    print(f'{host}: {project}', flush=True)
    output_lines = []
    deadline = time.monotonic() + timeout

    def turn(command, text):
        process = subprocess.Popen(command, cwd=project, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, stdin=subprocess.PIPE if text is not None else subprocess.DEVNULL, start_new_session=os.name != 'nt')
        if text is not None:
            process.stdin.write(text)
            process.stdin.close()
        def consume():
            with trace.open('a') as handle:
                for line in process.stdout:
                    try:
                        json.loads(line)
                        cleaned = clean(line)
                    except ValueError:
                        cleaned = json.dumps({'type':'host_output', 'text':clean(line.rstrip())}, ensure_ascii=False) + '\n'
                    output_lines.append(cleaned)
                    handle.write(cleaned)
                    handle.flush()
        reader = threading.Thread(target=consume, daemon=True)
        reader.start()
        started = time.monotonic()
        reason = None
        while process.poll() is None:
            if time.monotonic() >= deadline:
                reason = 'Native CLI exceeded the configured timeout'
                break
            if host == 'codex' and time.monotonic() - started > 60 and not list((project / '.agentic/jev').glob('event-*.json')):
                reason = 'No Codex JEV hook event observed; review project hooks in /hooks and rerun with --run-dir'
                break
            time.sleep(.25)
        if reason:
            if os.name != 'nt':
                os.killpg(process.pid, signal.SIGTERM)
            else:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                if os.name != 'nt':
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
        reader.join(timeout=10)
        return process.returncode, reason

    trace.write_text('')
    returncode, reason = turn(command, PROMPT if host in ('opencode', 'claude') else None)
    if not reason and returncode == 0 and not calculator_probe(project)[0]:
        followup = followup_turn(host, executable, command, trace)
        if followup:
            print(f'{host}: coordinator stopped before delivery; sending one approval follow-up', flush=True)
            returncode, reason = turn(*followup)
    if telegram:
        # The notifier sends from a detached child; give it a moment, then save evidence.
        for _ in range(40):
            if telegram.messages():
                break
            time.sleep(.25)
        (root / host / 'telegram.json').write_text(json.dumps(
            {'requests': [r['path'].replace('blackbox-token', '[token]') for r in telegram.requests],
             'messages': telegram.messages()}, ensure_ascii=False, indent=2))
        telegram.__exit__(None, None, None)
    output = ''.join(output_lines)
    if reason:
        return {'status': 'blocked' if 'hook' in reason else 'failed', 'reason': reason, 'project': str(project), 'trace': str(trace)}
    trace.write_text(output)
    if host == 'codex' and ('hooks need review' in output.lower() or 'untrusted hook' in output.lower() or 'review and trust' in output.lower()):
        return {'status': 'blocked', 'reason': 'Review project hooks in Codex /hooks and rerun with --run-dir.', 'project': str(project)}
    result = verify(project, trace, returncode, host)
    if 'usage limit' in output.lower() or 'insufficient_quota' in output:
        result.update(status='blocked', reason='Coding model usage quota is exhausted; JEV quota is separate')
    if host == 'claude' and ('Invalid API key' in output or 'Please run /login' in output):
        result.update(status='blocked', reason='Claude Code is not authenticated; run claude /login first')
    if 'provider.auth' in output or 'PERMISSION_DENIED' in output:
        result.update(status='blocked', reason='Coding provider authorization failed; JEV authentication is separate')
    return result


@contextmanager
def run_lock(root):
    root.mkdir(parents=True, exist_ok=True)
    lock = root / '.active-run'
    try:
        lock.mkdir()
    except FileExistsError:
        raise SystemExit('This artifact directory already has an active run. Inspect/stop that run before removing a stale .active-run directory.')
    try:
        yield
    finally:
        lock.rmdir()


def run_root(args):
    """Absolute artifact root (QR-D9): hosts run in the project directory, so a relative --run-dir would
    resolve AGENTIC_CONFIG_DIR and other derived paths against the wrong directory."""
    if args.run_dir:
        return args.run_dir.resolve()
    return ROOT / '.agentic-blackbox' / time.strftime('%Y%m%d-%H%M%S')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', choices=(*HOSTS, 'all'), default='all')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--verify-only', action='store_true', help='Recheck saved native execution without any model requests; requires --run-dir')
    parser.add_argument('--run-dir', type=Path, help='Reuse prepared projects after native hook trust review')
    parser.add_argument('--timeout', type=int, default=1200)
    args = parser.parse_args()
    if args.verify_only and not args.run_dir:
        parser.error('--verify-only requires --run-dir')
    root = run_root(args)
    endpoint = os.environ.get('JEV_API_URL') or 'https://api.typesafe.ai/v1/systemone'
    with run_lock(root):
        return execute(args, root, endpoint)


def execute(args, root, endpoint):
    results = {}
    for host in HOSTS if args.host == 'all' else (args.host,):
        try:
            project = Path(json.loads((root / host / 'project.json').read_text())['path']) if args.run_dir else prepare(host, root, endpoint)
            if args.run_dir and not args.verify_only:
                install_project(host, project, root, endpoint)
            if args.verify_only:
                previous = json.loads((root / 'results.json').read_text())[host]
                exit_code = 0 if previous.get('checks', {}).get('native_exit_success') or native_success(root / host / 'trace.jsonl') else 1
                result = verify(project, root / host / 'trace.jsonl', exit_code, host)
            elif args.prepare_only:
                result = {'status': 'prepared', 'project': str(project)}
                print(f'{host}: prepared {project}', flush=True)
            else:
                result = run(host, project, root, args.timeout)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            result = {'status': 'failed', 'reason': clean(str(error))}
        results[host] = result
        print(json.dumps(result, ensure_ascii=False), flush=True)
    root.mkdir(parents=True, exist_ok=True)
    (root / 'results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(r['status'] in ('passed', 'prepared') for r in results.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
