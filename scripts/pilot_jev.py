#!/usr/bin/env python3
"""Opt-in paid comparative JEV pilot (docs/jev-integration/epic/pilot.md). Never bypasses native trust or permissions.

Private target paths come from a Git-ignored JSON file; published results use task labels A/B/C only.
"""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'extensions/codex/hooks/jev'))
sys.path.insert(0, str(ROOT / 'scripts'))
from api import key_for  # noqa: E402
import blackbox_jev  # noqa: E402

RUN_SECONDS = 360
RUN_UNCACHED_TOKENS = 50_000
HOST_UNCACHED_TOKENS = 1_000_000
AREAS = ('devops,software', 'devops.infrastructure,software.backend,software.general')
WORKFLOWS = {'A': 'provision-environment', 'B': 'code-review-workflow', 'C': 'develop-feature'}
MODES = ('plain', 'fixed', 'jev')
ABLATIONS = ('workflow_only', 'models_only')
ABLATION_TASKS = ('A', 'C')
COORDINATOR = {'codex': 'gpt-6.1-sol', 'claude': 'sonnet', 'opencode': 'openai/gpt-6-luna'}
# Codex trusts hooks per absolute path; runs reuse the paths the user reviewed in /hooks.
# Outside any repository, so no parent AGENTS.md/CLAUDE.md leaks into a run.
PROJECTS = Path('/tmp/agentic-pilot')
CODEX_PATHS = {True: Path('/tmp/agentic-jev-blackbox-codex-8lk2ebos'), False: Path('/tmp/agentic-pilot-codex-fixed')}
TASKS = {
    'A': ('В каталоге configurations/grafana оцени, можно ли поднять Grafana через Docker с этой конфигурацией и '
          'импортировать дашборды из JSON-файлов этого каталога. Ничего не разворачивай, не запускай контейнеры, '
          'не читай и не создавай .env. Запиши результат в GRAFANA_FEASIBILITY.md в корне репозитория. Первая строка: '
          '`VERDICT: FEASIBLE` или `VERDICT: NOT FEASIBLE`. Далее: нужные файлы, способ импорта дашбордов, блокеры. '
          'Другие файлы не меняй.'),
    'B': ('Сделай поверхностный обзор производительности и качества Python-кода в src/. Не подключайся к базе данных, '
          'не читай .env, не меняй код. Запиши от 3 до 10 находок в REVIEW.md в корне репозитория. Каждая находка: '
          '`src/<путь>.py:<строка>`, проблема, предложение. Другие файлы не меняй.'),
    'C': ('Создай консольный калькулятор на Python: четыре операции (+, -, *, /), понятная ошибка при неверном вводе и '
          'при делении на ноль. Добавь тесты и проверь их запуском.'),
}
SUFFIX = ('Finish this bounded task as quickly as possible. Budget: at most 50,000 tokens across coordinator and subagents, '
          'six minutes total, at most one correction after checks. Deliver only the minimum sufficient result and evidence. '
          'Do not add optional improvements, deployment, or unrelated repairs. Preserve the supplied task and infrastructure '
          'limits. Report incomplete work honestly when the budget ends.')
REPORTS = {'A': 'GRAFANA_FEASIBILITY.md', 'B': 'REVIEW.md'}
QUOTA = re.compile(r'provider\.quota|usage limit has been reached|usage_limit_reached', re.I)
RUNTIME_DIRS = ('.agentic/', '.agentic-blackbox/', '__pycache__/', '.pytest_cache/')


def matrix(hosts, tasks):
    cells = [(h, t, m) for h in hosts for t in tasks for m in MODES]
    return cells + [(h, t, m) for h in hosts for t in tasks if t in ABLATION_TASKS for m in ABLATIONS]


def prompt(task, mode):
    explicit = mode in ('fixed', 'models_only')
    return (f'Выполни задачу по workflow {WORKFLOWS[task]}. ' if explicit else '') + TASKS[task] + '\n\n' + SUFFIX


def git(project, *args):
    return subprocess.run(['git', '-C', str(project), *args], check=True, capture_output=True, text=True).stdout


def copy_target(task, targets, project):
    """Clean clone of the pinned commit: untracked .env and local agent files never enter the copy."""
    if project.exists():
        shutil.rmtree(project)
    if task == 'C':
        project.mkdir(parents=True)
        git(project, 'init', '-q')
    else:
        source = targets[task]
        subprocess.run(['git', 'clone', '-q', '--no-hardlinks', source['repo'], str(project)], check=True)
        git(project, 'checkout', '-q', '--detach', source['commit'])
        git(project, 'remote', 'remove', 'origin')
    git(project, '-c', 'user.name=Agentic Pilot', '-c', 'user.email=pilot@localhost', 'commit', '-q', '--allow-empty', '-m', 'pilot: clean copy')


def install(host, project, jev, endpoint):
    agentic = ROOT / 'target/debug/agentic'
    command = ['upgrade', '--project-dir', str(project), '--force'] if (project / '.agentic.json').exists() else [
        'install', '--project-dir', str(project), '--agent-os', host, '--areas', AREAS[0], '--specializations', AREAS[1],
        '--no-doctor', '--enable-telegram', *(['--enable-jev', '--jev-api-url', endpoint] if jev else [])]
    result = subprocess.run([str(agentic), *command], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('agentic install failed: ' + result.stderr[-400:])


def pin_baseline(host, project, endpoint):
    """Workflow-only ablation: copy the JEV-disabled role profiles (their baseline pins) into the JEV copy."""
    baseline = project.parent / (project.name + '-baseline')
    if baseline.exists():
        shutil.rmtree(baseline)
    baseline.mkdir()
    git(baseline, 'init', '-q')
    install(host, baseline, False, endpoint)
    folder = {'codex': '.codex/agents', 'claude': '.claude/agents', 'opencode': '.opencode/agents'}[host]
    for profile in (baseline / folder).iterdir():
        shutil.copy2(profile, project / folder / profile.name)
    shutil.rmtree(baseline)


def prepare(host, task, mode, targets, workdir, endpoint):
    jev = mode in ('jev',) + ABLATIONS
    project = CODEX_PATHS[jev] if host == 'codex' and mode != 'plain' else workdir / f'{host}-{task}-{mode}'
    copy_target(task, targets, project)
    if mode != 'plain':
        install(host, project, jev, endpoint)
        if mode == 'workflow_only':
            pin_baseline(host, project, endpoint)
        git(project, 'add', '-A')
        git(project, '-c', 'user.name=Agentic Pilot', '-c', 'user.email=pilot@localhost', 'commit', '-q', '-m', 'pilot: agentic baseline')
    return project


def trust_ok(host, project, mode, trusted):
    """Codex JEV runs must use the exact hooks.json the user reviewed; other hosts have no hook trust store."""
    if host != 'codex' or mode == 'plain':
        return True
    digest = hashlib.sha256((project / '.codex/hooks.json').read_bytes()).hexdigest()
    return digest == trusted.get(str(project))


class Meter:
    """Live uncached-token accounting. Cached input is recorded separately and never counted toward the cap."""

    def __init__(self, host, project, started):
        self.host, self.project, self.started = host, project, started
        self.claude_messages, self.opencode_steps, self.sessions = {}, {}, {}

    def line(self, event):
        if self.host == 'claude' and event.get('type') == 'assistant':
            message = event.get('message') or {}
            usage = message.get('usage') or {}
            if message.get('id'):
                self.claude_messages[message['id']] = {
                    'model': message.get('model'), 'uncached': usage.get('input_tokens', 0) + usage.get('cache_creation_input_tokens', 0)
                    + usage.get('output_tokens', 0), 'cached': usage.get('cache_read_input_tokens', 0)}
        if self.host == 'opencode' and (event.get('part') or {}).get('type') == 'step-finish':
            tokens = event['part'].get('tokens') or {}
            cache = tokens.get('cache') or {}
            self.opencode_steps[event['part'].get('id')] = {
                'uncached': tokens.get('input', 0) + tokens.get('output', 0) + tokens.get('reasoning', 0) + cache.get('write', 0),
                'cached': cache.get('read', 0)}

    def codex_sessions(self):
        day = Path.home() / '.codex/sessions' / time.strftime('%Y/%m/%d', time.localtime(self.started))
        found = {}
        for path in day.glob('rollout-*.jsonl') if day.is_dir() else ():
            if path.stat().st_mtime < self.started:
                continue
            try:
                with path.open() as handle:
                    meta = json.loads(handle.readline()).get('payload') or {}
                if meta.get('cwd') != str(self.project):
                    continue
                usage, model = None, None
                with path.open() as handle:
                    for raw in handle:
                        event = json.loads(raw)
                        payload = event.get('payload') or {}
                        if event.get('type') == 'turn_context':
                            model = payload.get('model')
                        if payload.get('type') == 'token_count' and payload.get('info'):
                            usage = payload['info'].get('total_token_usage')
            except (OSError, ValueError):
                continue
            usage = usage or {}
            found[meta.get('id')] = {'model': model, 'agent_path': meta.get('agent_path') or '/root',
                                     'uncached': usage.get('input_tokens', 0) - usage.get('cached_input_tokens', 0) + usage.get('output_tokens', 0),
                                     'cached': usage.get('cached_input_tokens', 0)}
        self.sessions = found

    def rows(self):
        if self.host == 'codex':
            self.codex_sessions()
            return list(self.sessions.values())
        if self.host == 'claude':
            return list(self.claude_messages.values())
        return list(self.opencode_steps.values()) + list(self.sessions.values())

    def uncached(self):
        return sum(row['uncached'] for row in self.rows())


def opencode_children(trace, server, env, meter):
    """Final child accounting through the private server: subagent session IDs come from the parent's tool parts."""
    children = set()
    for raw in trace.read_text().splitlines():
        try:
            part = (json.loads(raw).get('part') or {})
        except ValueError:
            continue
        metadata = (part.get('state') or {}).get('metadata') or {}
        if part.get('type') == 'tool' and isinstance(metadata.get('sessionID'), str):
            children.add(metadata['sessionID'])
    for child in sorted(children):
        result = subprocess.run(['opencode', 'session', 'export', '--server', server, child], capture_output=True, text=True, env=env, timeout=60)
        try:
            info = json.loads(result.stdout)['info']
        except (ValueError, KeyError):
            meter.sessions[child] = {'model': None, 'uncached': None, 'cached': None, 'missing': True}
            continue
        tokens = info.get('tokens') or {}
        cache = tokens.get('cache') or {}
        meter.sessions[child] = {'model': (info.get('model') or {}).get('id'), 'cached': cache.get('read', 0),
                                 'uncached': tokens.get('input', 0) + tokens.get('output', 0) + tokens.get('reasoning', 0) + cache.get('write', 0)}


def host_env(host, project):
    env = os.environ.copy()
    env['PWD'] = str(project)
    for name in ('CODEX_REMOTE_PAYLOAD', 'CODEX_THREAD_ID', 'CODEX_SESSION_ID', *blackbox_jev.CLAUDE_SESSION_ENV):
        env.pop(name, None)
    for key in ('JEV_API_KEY', 'TYPESAFE_API_KEY'):
        value = key_for(ROOT, key)
        if value:
            env[key] = value
    if host == 'opencode':
        env['AGENTIC_JEV_MODEL_PROVIDER'] = 'openai'
        env['OPENCODE_PASSWORD'] = hashlib.sha256(os.urandom(16)).hexdigest()
    return env


def command(host, project, server=None):
    if host == 'codex':
        return [shutil.which('codex'), 'exec', '--json', '--skip-git-repo-check', '--sandbox', 'danger-full-access',
                '-m', COORDINATOR['codex'], '-C', str(project)]
    if host == 'claude':
        return [shutil.which('claude'), '-p', '--output-format', 'stream-json', '--verbose', '--permission-mode', 'acceptEdits',
                '--model', COORDINATOR['claude'], '--allowedTools', blackbox_jev.CLAUDE_ALLOWED_TOOLS]
    return [shutil.which('opencode'), 'run', '--server', server, '--model', COORDINATOR['opencode'], '--format', 'json']


def turn(argv, text, project, env, trace, meter, deadline):
    """One native turn in its own process group; the harness enforces time and uncached-token caps."""
    stdin = subprocess.PIPE if text is not None else subprocess.DEVNULL
    process = subprocess.Popen(argv, cwd=project, env=env, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, start_new_session=True)
    if text is not None:
        process.stdin.write(text)
        process.stdin.close()

    def consume():
        with trace.open('a') as handle:
            for raw in process.stdout:
                handle.write(blackbox_jev.clean(raw) if raw.strip().startswith('{') else json.dumps({'type': 'host_output', 'text': blackbox_jev.clean(raw.rstrip())}) + '\n')
                try:
                    meter.line(json.loads(raw))
                except ValueError:
                    pass
    reader = threading.Thread(target=consume, daemon=True)
    reader.start()
    reason, polled = None, 0.0
    while process.poll() is None:
        if time.monotonic() >= deadline:
            reason = 'time_cap'
        elif time.monotonic() - polled > 5:
            polled = time.monotonic()
            if meter.uncached() > RUN_UNCACHED_TOKENS:
                reason = 'token_cap'
        if reason:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
            break
        time.sleep(.25)
    reader.join(timeout=10)
    try:
        os.killpg(process.pid, signal.SIGKILL)  # no orphaned host children survive the run
    except ProcessLookupError:
        pass
    return process.returncode, reason


def changed_files(project):
    out = git(project, 'status', '--porcelain', '--untracked-files=all')
    files = [line[3:].strip('"') for line in out.splitlines()]
    return [f for f in files if not f.startswith(RUNTIME_DIRS) and '/__pycache__/' not in f]


def accept(task, project):
    """Frozen acceptance (docs/jev-integration/epic/pilot_acceptance.md); written before any pilot run."""
    changed = changed_files(project)
    if task == 'C':
        passed, evidence = blackbox_jev.calculator_probe(project)
        return {'accepted': passed, 'probe': evidence, 'changed': changed[:20]}
    report = project / REPORTS[task]
    text = report.read_text(errors='replace') if report.is_file() else ''
    checks = {'report': bool(text), 'only_report_changed': changed == [REPORTS[task]]}
    if task == 'A':
        names = {p.name for p in (project / 'configurations/grafana').rglob('*.json')}
        checks['verdict_line'] = text.splitlines()[0].strip() in ('VERDICT: FEASIBLE', 'VERDICT: NOT FEASIBLE') if text else False
        checks['dashboards_named'] = sum(name in text for name in names) >= 3
    else:
        import re
        refs = set(re.findall(r'(src/[\w./-]+\.py):(\d+)', text))
        valid = [r for r in refs if (project / r[0]).is_file() and 0 < int(r[1]) <= len((project / r[0]).read_text(errors='replace').splitlines())]
        checks['valid_findings'] = 3 <= len(valid) <= 10
    return {'accepted': all(checks.values()), 'checks': checks, 'changed': changed[:20]}


def jev_evidence(project):
    calls, usage, decisions = 0, {'input_tokens': 0, 'output_tokens': 0}, []
    for path in (project / '.agentic/jev').glob('event-*.json'):
        record = json.loads(path.read_text())
        result, context = record.get('result') or {}, record.get('context') or {}
        if result.get('usage'):
            calls += 1
            for key in usage:
                usage[key] += result['usage'].get(key, 0)
        if context.get('kind') in ('prompt', 'spawn', 'permission', 'observation'):
            decisions.append({'kind': context['kind'], 'agent': context.get('agent'), 'outcome': record.get('outcome'),
                              'status': result.get('status'), 'reason': result.get('reason_code'),
                              'model': result.get('model') or result.get('observed_model'), 'source': result.get('model_source'),
                              'workflow': (result.get('workflow') or {}).get('id') if isinstance(result.get('workflow'), dict) else None})
    prepared = [{k: json.loads(p.read_text()).get(k) for k in ('role', 'recommended_model', 'submitted_model', 'observed_model', 'application_status')}
                for p in (project / '.agentic/jev').glob('prepared-*.json')]
    return {'calls': calls, 'usage': usage, 'decisions': decisions, 'prepared': prepared}


def run_cell(host, task, mode, targets, out, endpoint, trusted):
    cell = out / f'{host}-{task}-{mode}'
    cell.mkdir(parents=True, exist_ok=True)
    project = prepare(host, task, mode, targets, PROJECTS, endpoint)
    if not trust_ok(host, project, mode, trusted):
        return {'status': 'blocked_untrusted_hooks'}
    env, trace, server_process, server = host_env(host, project), cell / 'trace.jsonl', None, None
    trace.write_text('')
    if host == 'opencode':
        port = 4300 + abs(hash(cell.name)) % 500
        server = f'http://127.0.0.1:{port}'
        server_process = subprocess.Popen(['opencode', 'serve', '--hostname', '127.0.0.1', '--port', str(port)], cwd=project, env=env,
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        for _ in range(60):
            try:
                urllib.request.urlopen(server + '/', timeout=1)
                break
            except OSError:
                time.sleep(.5)
    started = time.time()
    meter, deadline = Meter(host, project, started), time.monotonic() + RUN_SECONDS
    argv = command(host, project, server)
    text = prompt(task, mode)
    # Codex takes the prompt as an argument; Claude and OpenCode read it from stdin, as in blackbox_jev.
    code, reason = turn(argv + ([text] if host == 'codex' else []), None if host == 'codex' else text, project, env, trace, meter, deadline)
    turns, verdict = 1, accept(task, project)
    if not reason and not verdict['accepted'] and time.monotonic() < deadline - 30:
        followup = blackbox_jev.followup_turn(host, shutil.which(host), argv, trace)
        if followup:
            if host == 'codex':
                followup = ([followup[0][0], 'exec', 'resume', '--json', '--skip-git-repo-check',
                             '-c', 'sandbox_mode="danger-full-access"', *followup[0][-2:]], None)
            turns += 1
            code, reason = turn(*followup, project, env, trace, meter, deadline)
            verdict = accept(task, project)
    if host == 'opencode':
        opencode_children(trace, server, env, meter)
        os.killpg(server_process.pid, signal.SIGKILL)
    if QUOTA.search(trace.read_text(errors='replace')):
        # A provider quota stop is not an agent outcome; the cell counts as not run.
        result = {'host': host, 'task': task, 'mode': mode, 'status': 'quota_exhausted', 'elapsed_s': round(time.time() - started, 1)}
        (cell / 'result.json').write_text(json.dumps(result, indent=2))
        return result
    rows = meter.rows()
    measured = [r for r in rows if r.get('uncached') is not None]
    result = {'host': host, 'task': task, 'mode': mode, 'status': 'accepted' if verdict['accepted'] else (reason or 'rejected'),
              'cap': reason, 'exit': code, 'turns': turns, 'elapsed_s': round(time.time() - started, 1), 'acceptance': verdict,
              'tokens': {'uncached': sum(r['uncached'] for r in measured), 'cached': sum(r['cached'] for r in measured),
                         'complete': len(measured) == len(rows) and bool(rows), 'agents': rows},
              'cost_usd': claude_cost(trace) if host == 'claude' else None, 'jev': jev_evidence(project)}
    (cell / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def claude_cost(trace):
    cost = None
    for raw in trace.read_text().splitlines():
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        if event.get('type') == 'result' and event.get('total_cost_usd') is not None:
            cost = (cost or 0) + event['total_cost_usd']
    return cost


def export_anonymized(runs, path):
    """Every measured value per cell without paths, prompts, outputs or changed file names of private targets."""
    cells = []
    for result_path in sorted(Path(runs).glob('*/result.json')):
        r = json.loads(result_path.read_text())
        acceptance = r.get('acceptance') or {}
        tokens = r.get('tokens') or {}
        cells.append({
            'cell': result_path.parent.name, 'host': r.get('host'), 'task': r.get('task'), 'mode': r.get('mode'),
            'status': r.get('status'), 'cap': r.get('cap'), 'exit': r.get('exit'), 'turns': r.get('turns'), 'elapsed_s': r.get('elapsed_s'),
            'accepted': acceptance.get('accepted'), 'checks': acceptance.get('checks'), 'changed_files': len(acceptance.get('changed') or []),
            'probe_verified': (acceptance.get('probe') or {}).get('verified'),
            'tokens': {'uncached': tokens.get('uncached'), 'cached': tokens.get('cached'), 'complete': tokens.get('complete'),
                       'agents': [{k: a.get(k) for k in ('model', 'agent_path', 'uncached', 'cached', 'missing') if k in a}
                                  for a in tokens.get('agents') or []]},
            'cost_usd': r.get('cost_usd'), 'jev': r.get('jev'), 'note': r.get('note')})
    Path(path).write_text(json.dumps({'protocol': 'docs/jev-integration/epic/pilot_acceptance.md', 'cells': cells},
                                     ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--targets', type=Path, required=True, help='Git-ignored JSON: {"A": {"repo", "commit"}, "B": {...}}')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--hosts', default='codex,claude,opencode')
    parser.add_argument('--tasks', default='A,B,C')
    parser.add_argument('--only', help='Comma list of host-task-mode cells')
    parser.add_argument('--prepare-only', action='store_true', help='Create copies and installs; no model calls')
    parser.add_argument('--host-spent', type=int, default=0, help='Uncached tokens already spent on this host')
    parser.add_argument('--export', type=Path, help='Write anonymized per-cell measurements from --out and exit')
    args = parser.parse_args()
    if args.export:
        export_anonymized(args.out, args.export)
        return 0
    targets = json.loads(args.targets.read_text())
    trusted = targets.get('codex_trusted_hooks', {})
    endpoint = os.environ.get('JEV_API_URL') or 'https://api.typesafe.ai/v1/systemone'
    cells = matrix(args.hosts.split(','), args.tasks.split(','))
    if args.only:
        cells = [c for c in cells if '-'.join(c) in args.only.split(',')]
    spent = args.host_spent
    for host, task, mode in cells:
        name = f'{host}-{task}-{mode}'
        previous = args.out / name / 'result.json'
        if previous.exists() and json.loads(previous.read_text()).get('status') != 'quota_exhausted':
            continue  # never repeat a completed cell for a preferred result
        if args.prepare_only:
            project = prepare(host, task, mode, targets, PROJECTS, endpoint)
            print(json.dumps({'cell': name, 'project': str(project), 'trusted': trust_ok(host, project, mode, trusted)}), flush=True)
            continue
        if spent + RUN_UNCACHED_TOKENS > HOST_UNCACHED_TOKENS:
            print(json.dumps({'cell': name, 'status': 'skipped_host_budget', 'spent': spent}), flush=True)
            continue
        try:
            result = run_cell(host, task, mode, targets, args.out, endpoint, trusted)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            result = {'host': host, 'task': task, 'mode': mode, 'status': 'harness_error', 'reason': str(error)[-400:]}
            (args.out / name).mkdir(parents=True, exist_ok=True)
            (args.out / name / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
        spent += (result.get('tokens') or {}).get('uncached') or 0
        if result.get('status') == 'quota_exhausted':
            print(json.dumps({'host': host, 'status': 'stopped_quota_exhausted', 'after': name}), flush=True)
            break
        print(json.dumps({k: result.get(k) for k in ('host', 'task', 'mode', 'status', 'elapsed_s', 'turns')} |
                         {'uncached': (result.get('tokens') or {}).get('uncached'), 'jev_calls': (result.get('jev') or {}).get('calls')},
                         ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
