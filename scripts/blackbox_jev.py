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
from api import key_for, redact  # noqa: E402

PROMPT = 'разработай калькулятор'


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
    result = subprocess.run([str(ROOT / 'target/debug/agentic'), 'install', '--project-dir', str(project),
                             '--agent-os', host, '--areas', 'software', '--specializations',
                             'software.backend,software.general', '--enable-jev', '--jev-api-url', endpoint,
                             '--no-doctor'], capture_output=True, text=True)
    (root / host / 'install.log').write_text(clean(result.stdout + result.stderr))
    if result.returncode:
        raise RuntimeError('Agentic install failed; inspect install.log')


def verify(project, trace, exit_code):
    records = [json.loads(p.read_text()) for p in (project / '.agentic/jev').glob('event-*.json')]
    native_session = None
    for line in trace.read_text().splitlines():
        try:
            native = json.loads(line)
        except ValueError:
            continue
        native_session = native.get('thread_id') if native.get('type') == 'thread.started' else native.get('sessionID')
        if native_session:
            break
    prompts = [r for r in records if r['context']['kind'] == 'prompt' and r['context'].get('prompt') == PROMPT and r['context'].get('session_id') == native_session]
    tasks = {r['context'].get('task_id') for r in prompts}
    records = [r for r in records if r['context'].get('task_id') in tasks]
    workflow_records = [r for r in prompts if r['result'].get('workflow') and r['result']['status'] == 'evaluated']
    workflows = [r['result']['workflow'] for r in workflow_records]
    reads = [json.dumps(r['context'], ensure_ascii=False) for r in records if r['context']['kind'] == 'tool']
    workflow_applied = any(w['path'] in row for w in workflows for row in reads)
    routes = [r for r in records if r['context']['kind'] == 'spawn' and r['result'].get('model')]
    observed = [r for r in records if r['context']['kind'] == 'observation' and r['result'].get('observed_model')]
    # Match a child/role observation to the routed parent/role, rather than any mentioned model string.
    model_applied = any(a['result']['status'] == 'evaluated' and a['result']['model'] == b['result']['observed_model']
                        and a['context'].get('session_id') == b['context'].get('session_id')
                        and a['context'].get('agent') == b['context'].get('agent') for a in routes for b in observed)
    checks = {'native_exit_success': exit_code == 0, 'real_jev_workflow': bool(workflow_records),
              'workflow_read_by_agent': workflow_applied, 'model_applied_to_subagent': model_applied,
              'calculator_verified': False}
    # The agent selects the stack. Validate its delivered public entrypoint separately with explicit evidence.
    probe_command = [sys.executable, str(ROOT / 'scripts/blackbox_calculator_probe.py'), str(project)]
    verifier = os.environ.get('BLACKBOX_VERIFIER')
    if verifier:
        probe_command = [str(Path(verifier).resolve()), str(project)]
    try:
        probe = subprocess.run(probe_command, cwd=project, capture_output=True, text=True, timeout=30)
        evidence = json.loads(probe.stdout)
        checks['calculator_verified'] = probe.returncode == 0 and evidence.get('verified') is True
    except (OSError, ValueError, subprocess.TimeoutExpired):
        evidence = {'verified': False, 'reason': 'Independent calculator probe failed'}
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
    if host == 'codex':
        command = [executable, '--no-daemon', 'exec', '--json', '--skip-git-repo-check', '--sandbox', 'workspace-write', '-C', str(project), PROMPT]
    else:
        env['AGENTIC_JEV_MODEL_PROVIDER'] = 'openai'
        primary = os.environ.get('BLACKBOX_OPENCODE_MODEL', 'openai/gpt-5.5')
        if not primary.startswith('openai/'):
            raise ValueError('OpenCode blackbox is restricted to OpenAI models')
        command = [executable, 'run', '--standalone', '--model', primary, '--format', 'json']
    trace = root / host / 'trace.jsonl'
    print(f'{host}: {project}', flush=True)
    process = subprocess.Popen(command, cwd=project, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, stdin=subprocess.PIPE if host == 'opencode' else subprocess.DEVNULL, start_new_session=os.name != 'nt')
    if host == 'opencode':
        process.stdin.write(PROMPT)
        process.stdin.close()
    output_lines = []
    def consume():
        with trace.open('w') as handle:
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
    deadline = time.monotonic() + timeout
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
    output = ''.join(output_lines)
    if reason:
        return {'status': 'blocked' if 'hook' in reason else 'failed', 'reason': reason, 'project': str(project), 'trace': str(trace)}
    trace.write_text(output)
    if 'hooks need review' in output.lower() or 'untrusted hook' in output.lower() or 'review and trust' in output.lower():
        return {'status': 'blocked', 'reason': 'Review project hooks in Codex /hooks and rerun with --run-dir.', 'project': str(project)}
    result = verify(project, trace, process.returncode)
    if 'usage limit' in output.lower() or 'insufficient_quota' in output:
        result.update(status='blocked', reason='Coding model usage quota is exhausted; JEV quota is separate')
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', choices=('codex', 'opencode', 'all'), default='all')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--verify-only', action='store_true', help='Recheck saved native execution without any model requests; requires --run-dir')
    parser.add_argument('--run-dir', type=Path, help='Reuse prepared projects after native hook trust review')
    parser.add_argument('--timeout', type=int, default=1200)
    args = parser.parse_args()
    if args.verify_only and not args.run_dir:
        parser.error('--verify-only requires --run-dir')
    root = args.run_dir or ROOT / '.agentic-blackbox' / time.strftime('%Y%m%d-%H%M%S')
    endpoint = os.environ.get('JEV_API_URL') or 'https://api.typesafe.ai/v1/systemone'
    with run_lock(root):
        return execute(args, root, endpoint)


def execute(args, root, endpoint):
    results = {}
    for host in ('codex', 'opencode') if args.host == 'all' else (args.host,):
        try:
            project = Path(json.loads((root / host / 'project.json').read_text())['path']) if args.run_dir else prepare(host, root, endpoint)
            if args.run_dir and not args.verify_only:
                install_project(host, project, root, endpoint)
            if args.verify_only:
                previous = json.loads((root / 'results.json').read_text())[host]
                exit_code = 0 if previous.get('checks', {}).get('native_exit_success') else 1
                result = verify(project, root / host / 'trace.jsonl', exit_code)
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
